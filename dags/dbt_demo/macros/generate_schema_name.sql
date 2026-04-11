{#-
  Override padrão do dbt para evitar prefixar custom schemas com `target.schema`.
  Queremos que `+schema: silver_nyc_taxi` gere exatamente o schema `silver_nyc_taxi`
  no ClickHouse, sem concatenar com o default.
-#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
