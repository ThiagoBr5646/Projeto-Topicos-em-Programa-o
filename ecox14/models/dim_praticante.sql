-- Dimensao: quem treinou - perfil, coracao em repouso e habitos.
-- Grao: uma linha por praticante.
--
-- A fonte registra uma sessao por praticante e nao tem identificador de
-- pessoa: o praticante herda o numero da sessao. Se uma extracao futura
-- trouxer um id de pessoa, so esta dimensao muda.

select
    sessao_id                          as praticante_id,
    Gender                             as genero,
    Age                                as idade,
    "Weight (kg)"                      as peso_kg,
    "Height (m)"                       as altura_m,
    BMI                                as imc,
    Fat_Percentage                     as gordura_pct,
    Resting_BPM                        as bpm_repouso,
    "Water_Intake (liters)"            as agua_litros,
    "Workout_Frequency (days/week)"    as treinos_por_semana,
    Experience_Level                   as nivel_experiencia,
    experiencia
from {{ source('prata', 'gym_members_enriquecida') }}
