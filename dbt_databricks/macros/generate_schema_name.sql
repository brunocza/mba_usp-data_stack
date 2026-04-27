{#-
  Override do dbt para custom schemas literais (sem prefixo target.schema).
  Espelha o comportamento do projeto dbt_demo (ClickHouse).
-#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
