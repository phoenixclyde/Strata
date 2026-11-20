#pragma once
#include "strata_hip.h"
// r63: stream priority maps (fork strata_hip.h:135-136 parity)
#define cudaStreamCreateWithPriority hipStreamCreateWithPriority
#define cudaDeviceGetStreamPriorityRange hipDeviceGetStreamPriorityRange
#define cudaStreamNonBlocking hipStreamNonBlocking
