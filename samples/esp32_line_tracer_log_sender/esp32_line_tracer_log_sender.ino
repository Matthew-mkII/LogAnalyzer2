/*
 * LogAnalyzer2 向け ESP32 ライントレース + BLE ログ送信
 *
 * LineTracerOnOff（On/Off 制御）と LogAnalyzer2 CSV 形式を組み合わせた Arduino スケッチです。
 * Nordic UART Service（NUS）で notify 送信します。
 *
 * 必要ライブラリ（Arduino IDE）:
 *   ESP32 BLE Arduino（ボードパッケージに同梱）
 *
 * 配線例（ピンは下の定数で変更）:
 *   モーター … L298N 等のドライバ経由で LEFT/RIGHT PWM
 *   ラインセンサー … 反射型の analog 出力 → LINE_SENSOR_PIN
 *   開始ボタン … START_BUTTON_PIN（内部プルアップ、LOW で押下）
 *   （任意）バッテリー分圧 → BATTERY_ADC_PIN
 *
 * 使い方:
 *   1. ピン・edge を環境に合わせて設定
 *   2. ESP32 に書き込み、シリアルモニタは 115200 で確認可
 *   3. LogAnalyzer2 でスキャン → "LineTracer" を接続
 *   4. ボタン 1 回目: 閾値測定 / 2 回目: 走行開始
 */

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include <math.h>

// --- BLE (Nordic UART Service) ---
static const char *kDeviceName = "LineTracer";
static const char *kServiceUuid = "6e400001-b5a3-f393-e0a9-e50e24dcca9e";
static const char *kTxUuid = "6e400003-b5a3-f393-e0a9-e50e24dcca9e";

// --- ライントレース ---
static const int kLeftEdge = 1;
static const int kRightEdge = -1;
static int g_edge = kLeftEdge;  // kRightEdge に切り替え可

static const int kDriveSpeed = 100;   // LogAnalyzer2 の speed 列
static const int kSteerAngle = 55;    // LogAnalyzer2 の turn 列（On/Off 時の旋回指令）
static const int kLoopWaitMs = 10;
static const unsigned long kLoopCount = 6000;

// --- ピン割り当て（お使いの基板に合わせて変更） ---
static const int kLeftMotorPwmPin = 25;
static const int kLeftMotorIn1Pin = 26;
static const int kLeftMotorIn2Pin = 27;
static const int kRightMotorPwmPin = 14;
static const int kRightMotorIn1Pin = 12;
static const int kRightMotorIn2Pin = 13;
static const int kLineSensorPin = 34;
static const int kStartButtonPin = 0;
// static const int kBatteryAdcPin = 35;  // 未接続時はバッテリー列を空欄

// --- 走行状態 ---
static BLECharacteristic *g_txChar = nullptr;
static bool g_deviceConnected = false;
static unsigned long g_startMs = 0;
static int g_threshold = 0;
static bool g_running = false;
static unsigned long g_loopIndex = 0;
static float g_angleL = 0.0f;
static float g_angleR = 0.0f;
static int g_lastLeftPwm = 0;
static int g_lastRightPwm = 0;

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *server) override { g_deviceConnected = true; }

  void onDisconnect(BLEServer *server) override {
    g_deviceConnected = false;
    g_running = false;
    motorBrake();
    server->getAdvertising()->start();
  }
};

static void setupBle() {
  BLEDevice::init(kDeviceName);
  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new ServerCallbacks());

  BLEService *service = server->createService(kServiceUuid);
  g_txChar = service->createCharacteristic(
      kTxUuid, BLECharacteristic::PROPERTY_NOTIFY);
  g_txChar->addDescriptor(new BLE2902());
  service->start();

  BLEDevice::getAdvertising()->start();
  Serial.println("BLE advertising started: " + String(kDeviceName));
}

static void notifyLine(const char *line) {
  if (!g_deviceConnected || g_txChar == nullptr) {
    return;
  }

  const size_t len = strlen(line);
  const size_t chunkSize = 20;  // BLE MTU を考慮
  for (size_t offset = 0; offset < len; offset += chunkSize) {
    const size_t n = min(chunkSize, len - offset);
    g_txChar->setValue((uint8_t *)(line + offset), n);
    g_txChar->notify();
    delay(2);
  }
}

static int readReflection() {
  return analogRead(kLineSensorPin);
}

static bool isButtonPressed() {
  return digitalRead(kStartButtonPin) == LOW;
}

static void waitButtonPress() {
  while (!isButtonPressed()) {
    delay(50);
  }
  delay(30);  // チャタリング簡易除去
  while (isButtonPressed()) {
    delay(10);
  }
}

static int measureThreshold(int samples = 50) {
  long sum = 0;
  for (int i = 0; i < samples; ++i) {
    sum += readReflection();
    delay(20);
  }
  return (int)(sum / samples);
}

static int steerForEdge(bool onLine) {
  if (onLine) {
    return (g_edge == kLeftEdge) ? kSteerAngle : -kSteerAngle;
  }
  return (g_edge == kLeftEdge) ? -kSteerAngle : kSteerAngle;
}

static int speedToPwm(int speed) {
  return constrain(speed * 255 / 100, 0, 255);
}

static void setMotor(int in1Pin, int in2Pin, int pwmPin, int pwm) {
  pwm = constrain(pwm, -255, 255);
  if (pwm > 0) {
    digitalWrite(in1Pin, HIGH);
    digitalWrite(in2Pin, LOW);
    analogWrite(pwmPin, pwm);
  } else if (pwm < 0) {
    digitalWrite(in1Pin, LOW);
    digitalWrite(in2Pin, HIGH);
    analogWrite(pwmPin, -pwm);
  } else {
    digitalWrite(in1Pin, LOW);
    digitalWrite(in2Pin, LOW);
    analogWrite(pwmPin, 0);
  }
}

static void drive(int speed, int turn) {
  const int left = speed + turn;
  const int right = speed - turn;
  g_lastLeftPwm = speedToPwm(left);
  g_lastRightPwm = speedToPwm(right);
  setMotor(kLeftMotorIn1Pin, kLeftMotorIn2Pin, kLeftMotorPwmPin, g_lastLeftPwm);
  setMotor(kRightMotorIn1Pin, kRightMotorIn2Pin, kRightMotorPwmPin, g_lastRightPwm);
}

static void motorBrake() {
  g_lastLeftPwm = 0;
  g_lastRightPwm = 0;
  setMotor(kLeftMotorIn1Pin, kLeftMotorIn2Pin, kLeftMotorPwmPin, 0);
  setMotor(kRightMotorIn1Pin, kRightMotorIn2Pin, kRightMotorPwmPin, 0);
}

static void updateAngles() {
  // エンコーダ未使用時は PWM 積分で疑似角度を記録（LogAnalyzer2 の angleL/R 列用）
  const float dt = kLoopWaitMs / 1000.0f;
  g_angleL += g_lastLeftPwm * dt * 0.1f;
  g_angleR += g_lastRightPwm * dt * 0.1f;
}

static float readBatteryMv() {
#ifdef BATTERY_ADC_PIN
  const int raw = analogRead(BATTERY_ADC_PIN);
  return raw * (3.3f / 4095.0f) * 1000.0f * 2.0f;  // 分圧 1:1 想定
#else
  return NAN;
#endif
}

static void appendField(char *buffer, size_t bufferSize, bool *first, const char *text) {
  const size_t used = strlen(buffer);
  if (used >= bufferSize - 1) {
    return;
  }
  int written = snprintf(
      buffer + used,
      bufferSize - used,
      "%s%s",
      *first ? "" : ",",
      text);
  if (written > 0) {
    *first = false;
  }
}

static void appendFloat(char *buffer, size_t bufferSize, bool *first, float value) {
  char field[24];
  if (isnan(value)) {
    appendField(buffer, bufferSize, first, "");
    return;
  }
  if (fabsf(value - roundf(value)) < 0.000001f) {
    snprintf(field, sizeof(field), "%.0f", value);
  } else {
    snprintf(field, sizeof(field), "%.6f", value);
  }
  appendField(buffer, bufferSize, first, field);
}

static void formatLogLine(
    char *buffer,
    size_t bufferSize,
    unsigned long timeMs,
    int turn,
    int speed,
    float batteryMv,
    float hue,
    float saturation,
    float value,
    float roll,
    float yaw,
    float pitch) {
  buffer[0] = '\0';
  bool first = true;

  appendFloat(buffer, bufferSize, &first, (float)timeMs);
  appendFloat(buffer, bufferSize, &first, (float)turn);
  appendFloat(buffer, bufferSize, &first, (float)speed);
  appendFloat(buffer, bufferSize, &first, batteryMv);
  appendFloat(buffer, bufferSize, &first, g_angleL);
  appendFloat(buffer, bufferSize, &first, g_angleR);
  appendFloat(buffer, bufferSize, &first, hue);
  appendFloat(buffer, bufferSize, &first, saturation);
  appendFloat(buffer, bufferSize, &first, value);
  appendFloat(buffer, bufferSize, &first, 0.0f);  // Kp
  appendFloat(buffer, bufferSize, &first, 0.0f);  // Ki
  appendFloat(buffer, bufferSize, &first, 0.0f);  // Kd
  appendFloat(buffer, bufferSize, &first, roll);
  appendFloat(buffer, bufferSize, &first, yaw);
  appendFloat(buffer, bufferSize, &first, pitch);

  const size_t used = strlen(buffer);
  if (used + 2 < bufferSize) {
    buffer[used] = '\n';
    buffer[used + 1] = '\0';
  }
}

static void sendLogSample(int turn, int reflection) {
  char line[192];
  const unsigned long elapsed = millis() - g_startMs;
  const float sensorValue = reflection / 4095.0f;

  formatLogLine(
      line,
      sizeof(line),
      elapsed,
      turn,
      kDriveSpeed,
      readBatteryMv(),
      NAN,          // hue（カラーセンサー未使用時は空欄）
      NAN,          // saturation
      sensorValue,  // 反射値を value 列にマップ
      NAN,          // roll（IMU 未使用時は空欄）
      NAN,          // yaw
      NAN,          // pitch
  );
  notifyLine(line);
}

void setup() {
  Serial.begin(115200);

  pinMode(kLeftMotorIn1Pin, OUTPUT);
  pinMode(kLeftMotorIn2Pin, OUTPUT);
  pinMode(kRightMotorIn1Pin, OUTPUT);
  pinMode(kRightMotorIn2Pin, OUTPUT);
  pinMode(kStartButtonPin, INPUT_PULLUP);

  setupBle();
  motorBrake();

  Serial.println("Press button: calibrate threshold");
  waitButtonPress();
  g_threshold = measureThreshold();
  Serial.printf("Threshold = %d\n", g_threshold);

  Serial.println("Press button: start line trace");
  waitButtonPress();

  g_startMs = millis();
  g_running = true;
  g_loopIndex = 0;
  g_angleL = 0.0f;
  g_angleR = 0.0f;
}

void loop() {
  if (!g_running) {
    delay(100);
    return;
  }

  if (!g_deviceConnected) {
    motorBrake();
    delay(200);
    return;
  }

  if (g_loopIndex >= kLoopCount) {
    motorBrake();
    g_running = false;
    Serial.println("Line trace finished");
    return;
  }

  const int reflection = readReflection();
  const bool onLine = reflection > g_threshold;
  const int turn = steerForEdge(onLine);

  drive(kDriveSpeed, turn);
  updateAngles();
  sendLogSample(turn, reflection);

  ++g_loopIndex;
  delay(kLoopWaitMs);
}
