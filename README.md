# Projeto de Engenharia de Dados

Projeto da disciplina Tópicos em Programação — UNIFEI.

## Tema
Análise de dados de treino em academia (gym members exercise tracking)

## Pergunta norteadora
Quais características do praticante mais explicam as calorias queimadas por sessão?

Ela é o critério para criar coluna nova: se não dá para dizer em uma frase por que
a coluna ajuda a responder essa pergunta, a coluna não deveria existir.

## Estrutura
- `dados/bronze` — dado bruto, como veio da fonte
- `dados/prata` — dado limpo e padronizado
- `dados/ouro` — dado modelado, pronto para análise
- `src` — scripts do pipeline

### Scripts

| Script | O que faz |
|---|---|
| `src/ingerir.py` | Ingere a base de academia (Kaggle) na bronze |
| `src/ingerir_paises.py` | Ingere o cadastro de países (Banco Mundial) na bronze |
| `src/ingerir_indicador_paises.py` | Ingere o indicador por país e por ano, percorrendo todas as páginas |
| `src/explorar.py` | Gera o relatório de perfilamento da base de academia |
| `src/limpeza.py` | **Módulo** com as funções de limpeza que servem a qualquer fonte |
| `src/transformar_paises.py` | Bronze → prata da fonte de países |
| `src/transformar_indicador_paises.py` | Bronze → prata do indicador por país e ano |
| `src/transformar_gym_members.py` | Bronze → prata da base de academia |

`src/limpeza.py` não é executável: ele é importado. O critério para uma função morar
nele é um só — se a função menciona o nome de alguma fonte, ela fica no script daquela
fonte; se não menciona, é do módulo. Antes, `tirar_espacos` estava copiada em cada
script, e um defeito descoberto obrigava a corrigir em todos eles.

Ordem de execução, sempre a partir da raiz do projeto e **com a `.venv` ativada**
(o Python global não tem `pyarrow`, e sem ele `to_parquet` falha):

```
.\.venv\Scripts\Activate.ps1

python src/ingerir.py
python src/ingerir_paises.py
python src/ingerir_indicador_paises.py
python src/transformar_paises.py
python src/transformar_indicador_paises.py
python src/transformar_gym_members.py
```

## Fontes de dados

| Fonte | Formato | Acesso | Granularidade | Extraido | Link |
|---|---|---|---|---|---|
| Gym Members Exercise | CSV | token (Kaggle) | um praticante por linha | 20/08/2026 | kaggle.com/datasets/valakhorasani/gym-members-exercise-dataset |
| Banco Mundial — países | JSON | aberto | um país por linha, sem tempo | 20/08/2026 | api.worldbank.org/v2/country |
| Banco Mundial — indicador por país e ano | JSON | aberto | um país e um ano por linha | 17/09/2026 | api.worldbank.org/v2/country/all/indicator/SH.XPD.CHEX.PC.CD |

A terceira fonte é a única com tempo, e é o que permite perguntar sobre variação.
A série escolhida é `SH.XPD.CHEX.PC.CD` (gasto corrente em saúde per capita, em
dólares), de 2000 a 2023 — entre as séries disponíveis, é a variável de contexto
mais próxima do tema do projeto.

As duas últimas são fontes da mesma origem e de naturezas diferentes: o cadastro
descreve um retrato, o indicador descreve uma história. Por isso são dois scripts
de ingestão e duas pastas na bronze, não uma.

## Defeitos conhecidos das fontes
- A API do Banco Mundial devolve agregados regionais (como "World" e "Africa") junto
  com os países. No cadastro de países existe a coluna `region.value` para separá-los;
  **no indicador por país e ano não existe coluna de região**, e os agregados
  continuam na prata. A separação sai da junção com `dados/prata/paises.parquet`.
- A resposta do indicador vem **paginada** (o alerta de paginação dispara nesta fonte).
  `src/ingerir_indicador_paises.py` percorre todas as páginas e confere o total
  recebido contra o total informado pela API. Ignorar isso não gera erro nenhum:
  o script roda, o arquivo salva, o gráfico sai, e o número está errado.
- O indicador não tem dado para todo país em todo ano: 695 das 6360 linhas vêm sem
  valor.
- **No indicador, `countryiso3code` vem vazio nos cinco agregados por nível de renda**
  (High income, Low income, Lower middle income, Upper middle income, Not classified) —
  120 linhas, 24 anos cada. Essas linhas têm o código de 2 letras em `country.id`.
  Como ausente conta como repetido numa checagem de duplicidade, usar `countryiso3code`
  direto como chave acusava 96 "chaves repetidas" e apagava 96 linhas boas. Por isso
  existe a coluna `pais_codigo`.
- **Defeito da leitura, não da fonte**: o código de 2 letras da Namíbia é `NA`, e o
  pandas na configuração padrão lê `NA` como ausente. O CSV do indicador é lido com
  `keep_default_na=False, na_values=[""]`, para que só a célula vazia conte como
  ausente.
- A API informa `lastupdated` (data em que a fonte atualizou a série pela última vez).
  Ele responde à pergunta de atualidade e fica registrado na proveniência da bronze,
  não na tabela: é informação sobre o conjunto inteiro, e repetir em toda linha seria
  desperdício.

## Decisões de tratamento

### Banco Mundial — países (`transformar_paises.py`)
- Espaços removidos de nomes de coluna e de texto (ex.: valores de região como
  `Latin America & Caribbean ` vinham com espaço no fim).
- Agregados regionais separados: 78 linhas retiradas (de 295 originais, restando 217 países).
  Motivo: granularidade diferente da dos países — "World", "Africa" etc. não são países.
- Chave `id` (código de 3 letras do país) conferida quanto a duplicidade: 0 chaves repetidas
  entre os 217 países restantes.
- Longitude e latitude convertidas de texto para número (`pd.to_numeric`, `errors="coerce"`).
  Vazios/inválidos que viraram ausentes na conversão: 0 (os ausentes já vinham vazios no CSV
  de origem, não eram texto inválido).
- Valores extremos de longitude e latitude marcados por dois métodos, para comparar
  (sem remover nenhum):
  - longitude: 15 extremos pelo método IQR, 0 pelo z-score (limite 3 desvios-padrão).
  - latitude: 0 extremos por IQR, 0 por z-score.
  Divergência entre os métodos: o IQR é mais sensível em distribuições assimétricas
  (caso da longitude, que cobre o globo todo), por isso aponta mais candidatos que o z-score.
- Linhas com longitude fora de [-180, 180] ou latitude fora de [-90, 90] seriam removidas
  por erro geográfico comprovado: 0 em ambas as colunas (nenhum erro desse tipo na fonte).
- Coluna `capitalCity` vazia mantida como está. Não se aplica a todos os registros
  (territórios/nações sem capital declarada na fonte); o vazio aqui é a resposta certa,
  não um defeito.
- **Colunas de comparação criadas ao lado do rótulo original**: `regiao_chave` e
  `renda_chave` (sem acento, sem espaço sobrando, em minúscula). Uma coluna serve para
  comparar e juntar, a outra para mostrar — quem some com o acento na hora de exibir está
  jogando fora informação.
- **Nível de renda tipado como categoria com ordem** em `nivel_renda`
  (`Low income < Lower middle income < Upper middle income < High income`). Guardado como
  texto livre, nada impedia um `Hgih income` de entrar; declarada a escala, o que não está
  nela vira ausente — e é isso que se quer, porque "Not classified" não é nível de renda.
  Linhas fora da escala nesta extração: 0 (os 217 países estão todos classificados).
  O rótulo original continua em `incomeLevel.value`.
- Mapa de sinônimos de renda escrito de forma explícita no script (`MAPA_RENDA`): a
  classificação do Banco Mundial já usou `High income: OECD` e `High income: nonOECD` como
  categorias separadas. O mapa deixa o script funcionar também sobre uma bronze antiga,
  em vez de jogar essas linhas fora em silêncio.

### Banco Mundial — indicador por país e ano (`transformar_indicador_paises.py`)
- Coluna `date` convertida para **inteiro** (`Int64`), não para data. Um ano não tem mês,
  dia, hora nem fuso: converter para data não acrescenta informação, acrescenta precisão
  falsa. `Int64` com I maiúsculo é o inteiro do pandas que aceita ausente.
- Coluna `value` convertida para número com `errors="coerce"`, contando quantos ausentes
  já vinham da fonte e quantos apareceram na conversão (conversão que come dado em
  silêncio é o defeito que não avisa).
- Colunas sem informação removidas, contadas antes de apagar: `unit` e `obs_status` vêm
  vazias; `decimal` vem sempre com o mesmo valor. `indicator.id` e `indicator.value`
  também são constantes, mas ficaram — elas dizem qual série é esta, e isso é metadado
  proposital, não coluna inútil.
- `pais_codigo` criada como chave: `countryiso3code`, preenchida com `country.id` nas
  120 linhas em que a fonte deixou o iso3 vazio. Resultado: 0 linhas sem código.
- Granularidade conferida em `pais_codigo` + `date` (chave composta): 0 repetidas,
  0 ausentes na chave, 6360 linhas antes e 6360 depois — nada foi removido por
  duplicidade. A checagem separa "a fonte repetiu registro" de "a fonte não preencheu o
  código", que são problemas diferentes, e o script **para com erro** se a granularidade
  quebrar, em vez de seguir com a tabela errada.
- Conferência de plausibilidade da variação: 5 linhas com variação acima de 100% em
  módulo, sinalizadas e não removidas. Os extremos são eventos reais em série medida em
  dólar corrente (Argentina em 2002, −67%; Congo em 2001, −69%), não divisão por valor
  quase zero.
- `pais_chave` criada para a junção da próxima aula (o código de 3 letras é a chave boa;
  o nome padronizado serve de conferência).
- Agregados regionais mantidos, por falta de coluna de região nesta fonte — ver
  "Defeitos conhecidos".

### Academia (`transformar_gym_members.py`)
- Espaços removidos de nomes de coluna e de texto.
- Linhas idênticas repetidas: 0.
- `Gender` e `Workout_Type` tipadas como categoria **sem** ordem (nenhuma das duas tem
  escala natural); `treino_chave` criada ao lado para comparar e agrupar.
- `Experience_Level` (1, 2, 3) virou a categoria **com** ordem `experiencia`
  (`iniciante < intermediario < avancado`). É número, mas não se soma: 3 não é o triplo
  de 1. O número original continua na tabela.
- Pendente desta fonte: as checagens de qualidade da aula 5 (valor extremo por IQR e
  z-score, faixa válida por domínio) foram feitas só na fonte de países.

## Atributos derivados

Um atributo derivado é uma coluna nova, calculada a partir das que já existem, que
responde melhor à pergunta do que qualquer uma delas sozinha. A fonte publicou o que
ela achou útil; ninguém lá sabia o que este projeto queria perguntar.

Critério aplicado a cada um: uma frase explica por que a coluna ajuda a responder a
pergunta norteadora, ela não repete informação que já existe em outra coluna, e o
cálculo está em uma função com nome que diz o que ela faz.

### `calorias_por_hora` (academia)
`Calories_Burned / Session_Duration (hours)`, em kcal/h.

Serve à pergunta norteadora porque separa intensidade de duração: sem dividir, quem
fica duas horas em ritmo leve aparece como quem gasta mais. É a família "razão ou taxa"
— divide para tirar o efeito do tamanho.

Não repete coluna existente: as duas colunas de origem estão na fonte, a razão entre
elas não. Caso oposto, e por isso descartado: refazer o `BMI`, que a fonte **já** publica
derivado de peso e altura — seria coluna que só ocupa espaço e que um dia discorda da
original.

Ausente quando a duração é zero ou inválida (a divisão devolveria valor absurdo).
Faixa observada nesta extração: 540 a 930 kcal/h, média 720 — plausível para treino de
adulto. Valores fora de 200–1500 kcal/h são sinalizados, não removidos.

### `variacao_pct` (indicador por país e ano)
Variação percentual do indicador em relação ao ano anterior, por país.

Serve para comparar ritmo de crescimento entre países de tamanhos diferentes: a coluna
original esconde o que a derivada mostra — em valor absoluto as barras parecem todas
iguais e sempre subindo, e na variação aparece quando o crescimento desacelerou.

Ausente no primeiro ano de cada país, por definição, e também quando há buraco na série:
se o país tem 2010 e depois 2013, chamar isso de variação de um ano seria errado.
O cálculo ordena por país e ano antes de tudo — sem ordenar, a variação sairia contra a
linha anterior do arquivo, que pode ser outro ano ou outro país.

### `value_faixa` (indicador por país e ano)
Quartil do gasto per capita, como categoria ordenada
(`muito baixo < baixo < alto < muito alto`).

Serve para agrupar países comparáveis sem escolher corte arbitrário. `qcut` corta por
quantidade de registros (cada faixa fica com um quarto dos casos), diferente de `cut`,
que cortaria por valor em faixas de largura igual — aqui interessa a posição relativa
("gasta pouco ou muito comparado aos outros"), logo `qcut`.

Calculado **ano a ano**, não sobre o painel inteiro: o valor está em dólares correntes e
sobe com o tempo em quase todo país, então um quartil global misturaria décadas e diria
que 2001 gasta pouco. Ausente nos anos em que a fonte não tem dado suficiente para cortar
em quatro faixas (o último ano da série, tipicamente).

## Proveniência
- `dados/bronze/<fonte>/proveniencia.json` — de onde veio, quando, e quantos registros a
  fonte informou contra quantos foram recebidos (a conferência de paginação).
- `dados/prata/proveniencia.jsonl` — uma linha por execução de transformação, com as
  decisões tomadas e os números reais daquela execução, não fixos no texto.
