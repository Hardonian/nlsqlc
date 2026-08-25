# Query IR v2 Specification

nlsql Query IR v2 is a constrained S-expression grammar designed for deterministic multi-tenant SQL compilation, model output safety, and zero-SQL-injection code generation.

## Extensions in v2

1. **Multi-Type Joins**:
   - `(join inner table alias predicate)`
   - `(join left table alias predicate)`
   - `(join right table alias predicate)`
   - `(join full table alias predicate)`
2. **Boolean Operators**:
   - `(or expr1 expr2 ...)`
   - `(not expr)`
3. **Null Operations**:
   - `(is-null expr)`
   - `(is-not-null expr)`
4. **Scalar & String Manipulation**:
   - `(lower expr)`, `(upper expr)`, `(trim expr)`
   - `(concat expr1 expr2 ...)`
   - `(coalesce expr1 expr2 ...)`
5. **Distinct Aggregations & Math**:
   - `(count-distinct expr)`, `(sum-distinct expr)`
   - `(add a b)`, `(sub a b)`, `(div a b)`
6. **Window Frames**:
   - `(window expr (partition-by ...) (order-by ...))`

## Example Query IR v2

```lisp
(nlsql 2
  (query
    (from orders o)
    (join left customers c (eq (column o customer_id) (column c id)))
    (select
      (field (column o id) order_id)
      (field (coalesce (column c region) (param default_region text)) region)
      (field (count-distinct (column o id)) unique_orders))
    (where (and
      (gt (column o total_amount) (param min_total decimal))
      (is-not-null (column o status))))
    (group-by (column o id) (column c region))
    (order-by (ref unique_orders) desc)
    (limit 50)))
```
