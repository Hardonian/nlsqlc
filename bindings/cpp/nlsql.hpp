#pragma once
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include "nlsql/nlsql.h"

namespace nlsqlc {

inline void throw_status(nlsql_status status) {
    if (status != NLSQL_OK) throw std::runtime_error(nlsql_status_name(status));
}

class Context final {
public:
    explicit Context(const nlsql_config &config = {}) {
        throw_status(nlsql_context_create(&config, &context_));
    }
    ~Context() { nlsql_context_destroy(context_); }
    Context(const Context &) = delete;
    Context &operator=(const Context &) = delete;
    nlsql_context *get() const noexcept { return context_; }
private:
    nlsql_context *context_ = nullptr;
};

class Result final {
public:
    explicit Result(nlsql_compile_result *result) : result_(result) {}
    ~Result() { nlsql_compile_result_destroy(result_); }
    Result(const Result &) = delete;
    Result &operator=(const Result &) = delete;
    Result(Result &&other) noexcept : result_(std::exchange(other.result_, nullptr)) {}
    Result &operator=(Result &&other) noexcept {
        if (this != &other) {
            nlsql_compile_result_destroy(result_);
            result_ = std::exchange(other.result_, nullptr);
        }
        return *this;
    }
    nlsql_sql_view sql() const noexcept { return nlsql_result_sql(result_); }
    nlsql_status status() const noexcept { return nlsql_result_status(result_); }
    const char *error() const noexcept { return nlsql_result_error(result_); }
    const char *canonical_ir() const noexcept { return nlsql_result_canonical_ir(result_); }
    const char *manifest() const noexcept { return nlsql_result_manifest(result_); }
    size_t parameter_count() const noexcept { return nlsql_result_param_count(result_); }
    nlsql_param_view parameter(size_t index) const noexcept { return nlsql_result_param(result_, index); }
    nlsql_risk risk() const noexcept { return nlsql_result_risk(result_); }
    unsigned complexity() const noexcept { return nlsql_result_complexity(result_); }
    uint64_t fingerprint() const noexcept { return nlsql_result_fingerprint(result_); }
    double relevance_score() const noexcept { return nlsql_result_relevance_score(result_); }
    nlsql_compile_result *get() const noexcept { return result_; }
private:
    nlsql_compile_result *result_;
};

inline Result finish_result(nlsql_status status, nlsql_compile_result *result) {
    if (status != NLSQL_OK) {
        nlsql_compile_result_destroy(result);
        throw_status(status);
    }
    return Result(result);
}

inline Result compile_ir(Context &context, const nlsql_compile_request &request) {
    nlsql_compile_result *result = nullptr;
    return finish_result(nlsql_compile_ir(context.get(), &request, &result), result);
}

inline Result compile_set(Context &context, const nlsql_set_request &request) {
    nlsql_compile_result *result = nullptr;
    return finish_result(nlsql_compile_set(context.get(), &request, &result), result);
}

inline Result compile_cte(Context &context, const nlsql_cte_request &request) {
    nlsql_compile_result *result = nullptr;
    return finish_result(nlsql_compile_cte(context.get(), &request, &result), result);
}

inline Result compile_question(Context &context, const nlsql_question_request &request) {
    nlsql_compile_result *result = nullptr;
    return finish_result(nlsql_compile_question(context.get(), &request, &result), result);
}

} // namespace nlsqlc
