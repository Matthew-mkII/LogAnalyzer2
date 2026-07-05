// SPDX-License-Identifier: MIT

#include "log_sender.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

#include <syssvc/serial.h>
#include "serial/serial.h"

#include <spike/hub/bluetooth.h>
#include <spike/hub/imu.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

void log_sender_row_clear(log_sender_row_t *row) {
  if (row == NULL) {
    return;
  }
  memset(row, 0, sizeof(*row));
}

void log_sender_init(log_sender_t *self) {
  if (self == NULL) {
    return;
  }
  self->serial_open = E_OBJ;
  self->start_ms = 0;
  self->yaw_angle = 0.0f;
  self->imu_interval_us = 10000;
}

static void log_sender_init_imu(void) {
  while (hub_imu_init() == PBIO_ERROR_FAILED) {
    dly_tsk(100000);
  }
}

log_sender_result_t log_sender_open_ble(log_sender_t *self) {
  if (self == NULL) {
    return LOG_SENDER_ERR_BLE;
  }

  log_sender_init_imu();

  if (self->serial_open != E_OK) {
    self->serial_open = serial_opn_por(SIO_BLUETOOTH_PORTID);
  }

  get_tim(&self->start_ms);
  self->yaw_angle = 0.0f;

  if (self->serial_open != E_OK) {
    return LOG_SENDER_ERR_BLE;
  }
  return LOG_SENDER_OK;
}

bool log_sender_is_connected(const log_sender_t *self) {
  bool connected = false;

  if (self == NULL || self->serial_open != E_OK) {
    return false;
  }
  hub_bluetooth_is_connected(&connected);
  return connected;
}

unsigned long log_sender_elapsed_ms(const log_sender_t *self) {
  SYSTIM now = 0;

  if (self == NULL) {
    return 0;
  }
  get_tim(&now);
  return (unsigned long)now - (unsigned long)self->start_ms;
}

int log_sender_format_row(char *buffer, size_t buffer_size, const log_sender_row_t *row) {
  if (buffer == NULL || buffer_size == 0 || row == NULL) {
    return -1;
  }

  if (row->include_time) {
    return snprintf(
        buffer,
        buffer_size,
        "%lu,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n",
        row->time_ms,
        row->turn,
        row->speed,
        row->battery,
        row->angleL,
        row->angleR,
        row->hue,
        row->saturation,
        row->value,
        row->Kp,
        row->Ki,
        row->Kd,
        row->roll,
        row->yaw,
        row->pitch);
  }

  return snprintf(
      buffer,
      buffer_size,
      "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n",
      row->turn,
      row->speed,
      row->battery,
      row->angleL,
      row->angleR,
      row->hue,
      row->saturation,
      row->value,
      row->Kp,
      row->Ki,
      row->Kd,
      row->roll,
      row->yaw,
      row->pitch);
}

void log_sender_send_raw(log_sender_t *self, const char *line) {
  if (self == NULL || line == NULL || !log_sender_is_connected(self)) {
    return;
  }
  serial_wri_dat(SIO_BLUETOOTH_PORTID, line, (uint16_t)strlen(line));
}

void log_sender_send_row(log_sender_t *self, const log_sender_row_t *row) {
  char line[192];

  if (self == NULL || row == NULL) {
    return;
  }
  if (log_sender_format_row(line, sizeof(line), row) <= 0) {
    return;
  }
  log_sender_send_raw(self, line);
}

void log_sender_read_imu(log_sender_t *self, log_sender_row_t *row, int dt_us) {
  float accel[3];
  float angv[3];
  float ax;
  float ay;
  float az;
  float denom;
  float wz;

  if (self == NULL || row == NULL) {
    return;
  }

  hub_imu_get_acceleration(accel);
  ax = accel[0];
  ay = accel[1];
  az = accel[2];
  denom = sqrtf(ay * ay + az * az);

  row->pitch = atan2f(-ax, denom) * 180.0f / (float)M_PI;
  row->roll = atan2f(ay, az) * 180.0f / (float)M_PI;

  hub_imu_get_angular_velocity(angv);
  wz = angv[2];
  if (wz > -1.0f && wz < 1.0f) {
    wz = 0.0f;
  }
  if (dt_us > 0) {
    self->yaw_angle += wz * ((float)dt_us / 1000000.0f);
  }
  row->yaw = self->yaw_angle;
}
