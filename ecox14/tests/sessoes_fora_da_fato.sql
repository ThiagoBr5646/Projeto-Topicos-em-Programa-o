-- Passa quando devolve ZERO linhas.
--
-- Toda sessao da prata precisa estar na fato. A fato filtra
-- "codigo is not null" (treino sem par no Compendio); se algum dia esse
-- filtro tirar sessoes, este teste falha e diz quantas ficaram de fora.
-- E a conta "antes = depois" da juncao da aula 7, cobrada sozinha.

select
    (select count(*) from {{ source('prata', 'gym_members_enriquecida') }}) as sessoes_na_prata,
    (select count(*) from {{ ref('fato_sessao') }})                         as sessoes_na_fato
where (select count(*) from {{ source('prata', 'gym_members_enriquecida') }})
   <> (select count(*) from {{ ref('fato_sessao') }})
