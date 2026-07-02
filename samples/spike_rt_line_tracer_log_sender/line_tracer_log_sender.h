// SPDX-License-Identifier: MIT
/*
 * line_tracer_log_sender.h
 *
 * SPIKE-RT カーネルタスクの宣言とビルド定数を定義します。
 * .cfg ファイルからインクルードされ、main_task のプロトタイプを公開します。
 */
#include <kernel.h>

/* メインタスクの優先度（数値が小さいほど高優先度） */
#define MAIN_PRIORITY 5

/* メインタスクのスタックサイズ [バイト] */
#ifndef STACK_SIZE
#define STACK_SIZE 4096
#endif

#ifndef TOPPERS_MACRO_ONLY
/* SPIKE-RT が起動時に呼び出すエントリポイント（line_tracer_log_sender.cpp で実装） */
extern void main_task(intptr_t exinf);
#endif
