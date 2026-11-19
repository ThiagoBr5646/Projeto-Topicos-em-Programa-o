-- Fato: os numeros de cada sessao de treino.
-- Grao: uma linha = uma sessao de treino de um praticante.
--
-- O "where codigo is not null" e o filtro de integridade que veio da
-- juncao da aula 7: so entra a sessao cujo treino existe na dim_treino.

select
    sessao_id,
    sessao_id                    as praticante_id,
    treino_chave                 as treino_id,
    "Session_Duration (hours)"   as duracao_h,
    Calories_Burned              as calorias_base,
    Avg_BPM                      as bpm_medio,
    Max_BPM                      as bpm_max,
    calorias_por_hora,
    calorias_met,
    razao_base_met
from {{ source('prata', 'gym_members_enriquecida') }}
where codigo is not null
