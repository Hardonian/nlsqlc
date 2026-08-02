# Fuzzing

The parser harness is `fuzz/fuzz_nlsql.c` and exercises arbitrary bounded bytes through the public `nlsql_compile_ir` entry point with a trusted fixture schema and policy.

Build with Clang/libFuzzer:

    CC=clang cmake -S . -B build/fuzz -DNLSQL_BUILD_TESTS=OFF -DNLSQL_BUILD_CLI=OFF -DNLSQL_BUILD_FUZZ=ON
    cmake --build build/fuzz --target nlsql-fuzz
    ./build/fuzz/nlsql-fuzz -max_total_time=60 fuzz-corpus

The harness never executes SQL, opens files, or uses network input. Inputs are capped at the library IR limit and every result is released.
