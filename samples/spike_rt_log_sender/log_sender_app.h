// SPDX-License-Identifier: MIT
/*
 * log_sender_app.h
 *
 * SPIKE-RT カーネルタスク設定（.cfg からインクルード）。
 */
#ifndef LOG_SENDER_APP_H
#define LOG_SENDER_APP_H

#include <kernel.h>

#define MAIN_PRIORITY 5

#ifndef STACK_SIZE
#define STACK_SIZE 4096
#endif

#ifndef TOPPERS_MACRO_ONLY
extern void main_task(intptr_t exinf);
#endif

#endif /* LOG_SENDER_APP_H */
