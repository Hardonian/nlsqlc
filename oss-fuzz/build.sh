#!/bin/bash -eu
cd "$SRC/nlsqlc"
cmake -S . -B build-oss-fuzz -GNinja -DNLSQL_BUILD_TESTS=OFF -DNLSQL_BUILD_CLI=OFF -DNLSQL_BUILD_FUZZ=ON
cmake --build build-oss-fuzz --target nlsql-fuzz
mkdir -p "$OUT"
cp build-oss-fuzz/nlsql-fuzz "$OUT/nlsql-fuzz"
cp fuzz-corpus/seed "$OUT/nlsql-fuzz_seed_corpus"