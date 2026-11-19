-- Devolve as sessoes com calorias por hora fora da faixa plausivel para
-- treino de adulto (aula 6). Mesmos limites de FAIXA_CALORIAS_HORA em
-- src/config.py, declarados como vars no dbt_project.yml.
--
-- severity='warn': a decisao da aula 6 foi SINALIZAR, nao remover. O
-- teste mostra quantas sao (WARN) e o pipeline segue. Para ver quais:
--     dbt test --select calorias_por_hora_plausivel --store-failures

{{ config(severity='warn') }}

select sessao_id, treino_id, duracao_h, calorias_base, calorias_por_hora
from {{ ref('fato_sessao') }}
where calorias_por_hora not between {{ var('kcal_h_minimo') }}
                                and {{ var('kcal_h_maximo') }}
