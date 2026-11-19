-- Passa quando devolve ZERO linhas.
--
-- A view junta a fato com as duas dimensoes por join interno. Se uma
-- sessao perder o praticante ou o treino, ela some da view sem avisar;
-- se uma dimensao repetir a chave, a sessao aparece duas vezes. Nos dois
-- casos a contagem da view deixa de bater com a da fato.

select
    (select count(*) from {{ ref('fato_sessao') }})        as linhas_na_fato,
    (select count(*) from {{ ref('vw_sessao_completa') }}) as linhas_na_view
where (select count(*) from {{ ref('fato_sessao') }})
   <> (select count(*) from {{ ref('vw_sessao_completa') }})
