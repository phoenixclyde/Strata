#pragma once
// r25 numeric probe (D45 bisection).  Compiled into strata_mmq; enabled at runtime by STRATA_NP=1.
// Every scan point proves it ran (NPSCAN on first sight) before a negative result may be believed (D48).
namespace strata::prefill::mmq::nprobe {
bool on();
void set_layer(int l);
int  layer();
void scan(const void* ptr, long long n, const char* tag, void* stream);
void spec_check(const void* spec, int n, long long rows_expect, const int* bounds, void* stream);
}
