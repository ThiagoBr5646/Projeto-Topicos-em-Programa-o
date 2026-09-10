# Projeto de Engenharia de Dados

Projeto da disciplina Tópicos em Programação — UNIFEI.

## Tema
Análise de dados de treino em academia (gym members exercise tracking)

## Estrutura
- `dados/bronze` — dado bruto, como veio da fonte
- `dados/prata` — dado limpo e padronizado
- `dados/ouro` — dado modelado, pronto para análise
- `src` — scripts do pipeline

## Fontes de dados

| Fonte | Formato | Acesso | Extraido | Link |
|---|---|---|---|---|
| Gym Members Exercise | CSV | token (Kaggle) | 20/08/2026 | kaggle.com/datasets/valakhorasani/gym-members-exercise-dataset |
| Banco Mundial | JSON | aberto | 20/08/2026 | api.worldbank.org/v2/country |

## Defeitos conhecidos das fontes
- A API do Banco Mundial devolve agregados regionais (como "World" e "Africa") junto com os países.

## Decisões de tratamento

### Banco Mundial
- Espaços removidos de nomes de coluna e de texto (ex.: valores de região como `Latin America & Caribbean ` vinham com espaço no fim).
- Agregados regionais separados: 78 linhas retiradas (de 295 originais, restando 217 países).
  Motivo: granularidade diferente da dos países — "World", "Africa" etc. não são países.
- Chave `id` (código de 3 letras do país) conferida quanto a duplicidade: 0 chaves repetidas entre os 217 países restantes.
- Longitude e latitude convertidas de texto para número (`pd.to_numeric`, `errors="coerce"`).
  Vazios/inválidos que viraram ausentes na conversão: 0 (os ausentes já vinham vazios no CSV de origem, não eram texto inválido).
- Valores extremos de longitude e latitude marcados por dois métodos, para comparar (sem remover nenhum):
  - longitude: 15 extremos pelo método IQR, 0 pelo z-score (limite 3 desvios-padrão).
  - latitude: 0 extremos por IQR, 0 por z-score.
  Divergência entre os métodos: o IQR é mais sensível em distribuições assimétricas (caso da longitude, que cobre o globo todo), por isso aponta mais candidatos que o z-score.
- Linhas com longitude fora de [-180, 180] ou latitude fora de [-90, 90] seriam removidas por erro geográfico comprovado: 0 em ambas as colunas (nenhum erro desse tipo na fonte).
- Coluna `capitalCity` vazia mantida como está. Não se aplica a todos os registros (territórios/nações sem capital declarada na fonte); o vazio aqui é a resposta certa, não um defeito.
