#include <caml/alloc.h>
#include <caml/callback.h>
#include <caml/memory.h>
#include <caml/mlvalues.h>
#include <caml/threads.h>

#include <stdlib.h>
#include <string.h>

static const value *dispatch = NULL;
static int runtime_started = 0;

static char *call_with_domain_lock(const char *request) {
  CAMLparam0();
  CAMLlocal2(input, result);
  input = caml_copy_string(request);
  result = caml_callback(*dispatch, input);
  char *copy = strdup(String_val(result));
  CAMLreturnT(char *, copy);
}

char *mahjong_ffi_call(const char *request) {
  if (!runtime_started) {
    char *argv[] = {(char *)"mahjong_ffi", NULL};
    caml_startup_pooled(argv);
    dispatch = caml_named_value("mahjong_ffi_dispatch");
    runtime_started = 1;
  }
  char *copy = call_with_domain_lock(request);
  return copy;
}

void mahjong_ffi_free(char *value) { free(value); }

int mahjong_ffi_abi_version(void) { return 1; }
