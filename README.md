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