# Projeto de Engenharia de Dados

Projeto da disciplina Tópicos em Programação — UNIFEI.

## Tema
Análise de dados de treino em academia (Gym Members Exercise Dataset, Kaggle),
enriquecida com o gasto de energia de cada tipo de treino (Compêndio de Atividades
Físicas 2024).

## Pergunta norteadora
Quais características do praticante mais explicam as calorias queimadas por sessão?

Ela é o critério para criar coluna nova: se não dá para dizer em uma frase por que
a coluna ajuda a responder essa pergunta, a coluna não deveria existir.

## Estrutura
- `dados/bronze` — dado bruto, como veio da fonte
- `dados/prata` — dado limpo e padronizado, inclusive a tabela enriquecida (Parquet)
- `dados/ouro/projeto.duckdb` — o banco: esquema `prata` (a prata carregada) e esquema
  `ouro` (o modelo estrela, construído pelo dbt)
- `src` — o pipeline, em Python
- `ecox14` — o projeto dbt que constrói e testa a camada Ouro
- `dashboard` — o painel (Streamlit), que só lê a Ouro
- `relatorios` — relatório de perfilamento (gerado, fica fora do git)
- `apresentacao` — apresentação interativa e roteiro de fala

### Scripts

| Arquivo | O que faz |
|---|---|
| `src/pipeline.py` | **Ponto de entrada.** Roda as cinco etapas na ordem, com log e retomada |
| `src/config.py` | Caminhos, fontes, faixas de plausibilidade e a configuração do log |
| `src/ingerir.py` | Etapa *ingestao*: baixa a base do Kaggle para a bronze e confere o Compêndio |
| `src/transformar_gym_members.py` | Etapa *transformacao*: academia, bronze → prata |
| `src/transformar_compendio.py` | Etapa *transformacao*: Compêndio, bronze → prata |
| `src/enriquecer_gym_members.py` | Etapa *enriquecimento*: junta academia e Compêndio (continua na prata) |
| `src/carga.py` | Etapa *carga*: abre o DuckDB e carrega a prata no esquema `prata` |
| `ecox14/` (dbt) | Etapa *modelagem*: constrói e testa o esquema `ouro` |
| `src/limpeza.py` | **Módulo** com as funções de limpeza que servem a qualquer fonte |
| `src/juncao.py` | **Módulo** com as funções de junção que servem a qualquer par de tabelas |
| `src/explorar.py` | Fora do pipeline: gera o relatório de perfilamento |
| `src/ler_dados.py` | Fora do pipeline: leitura rápida da bronze |
| `dashboard/consultas.py` | As consultas de leitura do painel (todo o SQL de leitura mora aqui) |
| `dashboard/painel.py` | A tela do painel, sem nenhuma linha de SQL |

`src/limpeza.py` e `src/juncao.py` não são executáveis: eles são importados. O critério
para uma função morar neles é um só — se a função menciona o nome da fonte (o tipo de
treino da academia, o código do Compêndio), ela fica no script da fonte; se não
menciona, é do módulo e serve para qualquer base que entrar no projeto.

## Como rodar

Com a `.venv` ativada (o Python global não tem `pyarrow` nem o `dbt`):

```
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python src/pipeline.py                  # tudo, desde o Kaggle
python src/pipeline.py transformacao    # retoma daqui (não toca no Kaggle)
python src/pipeline.py modelagem        # só o dbt: reconstrói e testa a Ouro

streamlit run dashboard/painel.py       # o painel, depois do pipeline
```

Os caminhos saem do `config.py`, calculados a partir do próprio arquivo: os comandos
funcionam de qualquer pasta, não só da raiz.

Na primeira execução depois das aulas 8 a 11, rode a partir de `transformacao` (ou o
pipeline inteiro): a prata ganhou a coluna `sessao_id`, e a Ouro depende dela.

`Database Error: file is locked`: o banco está aberto em outro programa (o painel no
meio de uma consulta, o `duckdb.exe -ui`, outro terminal). Feche e rode de novo. Como a
pasta do projeto está no OneDrive, a sincronização também pode segurar o arquivo por
alguns segundos.

O `ingerir.py` precisa de um token do Kaggle configurado. O arquivo `kaggle.json`
está no `.gitignore` e nunca vai para o repositório. Se o download falhar e a bronze já
tiver uma extração, o pipeline segue com ela e deixa um `WARNING` dizendo qual arquivo
usou (ver [Pipeline](#pipeline-aula-8)). O Compêndio não tem script de ingestão: a
página é pública, mas não tem API nem arquivo para baixar, e a tabela foi copiada para
CSV (detalhes em [Fontes de dados](#fontes-de-dados)).

## Fontes de dados

| Fonte | Formato | Acesso | Granularidade | Extraído | Link |
|---|---|---|---|---|---|
| Gym Members Exercise Dataset (autor `valakhorasani`) | CSV | token (Kaggle) | um praticante numa sessão por linha | 20/08/2026 | kaggle.com/datasets/valakhorasani/gym-members-exercise-dataset |
| 2024 Adult Compendium of Physical Activities, seção *Conditioning Exercise* | tabela em página HTML, copiada para CSV | público, sem token | uma atividade física por linha | 22/10/2026 | pacompendium.com/conditioning-exercise |

### Academia (Kaggle)
973 linhas e 15 colunas, que se dividem em quatro grupos:

- **Perfil:** `Age`, `Gender`, `Weight (kg)`, `Height (m)`, `BMI`, `Fat_Percentage`
- **Coração:** `Max_BPM`, `Avg_BPM`, `Resting_BPM`
- **Sessão:** `Session_Duration (hours)`, `Calories_Burned`, `Workout_Type`
- **Hábitos:** `Water_Intake (liters)`, `Workout_Frequency (days/week)`,
  `Experience_Level` (1 a 3)

### Compêndio de Atividades Físicas
86 linhas e 3 colunas: `Specific Activity Code` (código de 5 dígitos, com zero à
esquerda), `MET Value` e `Activity Description`.

MET é o gasto de energia de uma atividade em múltiplos do gasto em repouso. Um MET
equivale a cerca de 1 kcal por kg de peso por hora, então a estimativa de uma sessão é
`MET × peso (kg) × duração (h)`.

Referência: Herrmann SD et al. *2024 Adult Compendium of Physical Activities: A third
update of the energy costs of human activities.* J Sport Health Sci. 2024;13(1):6-12.
doi:10.1016/j.jshs.2023.10.010

A tabela da página foi copiada para CSV sem alterar código, MET nem descrição, com o
cabeçalho da página, e conferida código a código com o PDF da mesma seção.

## Defeitos conhecidos das fontes

### Academia (Kaggle)
- **A base é sintética.** A página da fonte apresenta os dados como registros de
  membros de academia, mas não informa como foram coletados (academia, aparelho,
  período). As 973 linhas seguem exatamente a fórmula

  `Calories_Burned = round(Session_Duration (hours) × Avg_BPM × s × i)`

  com `s = 5,5` para `Male` e `5,0` para `Female`, e `i = 0,9` quando `Age > 40`
  (`1,0` caso contrário). A diferença máxima entre a fórmula e a coluna é 0,5 kcal,
  que é o arredondamento. Peso, tipo de treino, experiência e % de gordura **não
  entram na conta**.
- Sinais que apontavam para dado gerado antes da fórmula aparecer:
  - idade e BPM médio têm o desvio-padrão de uma distribuição uniforme nas mesmas
    faixas (idade 18–59: 12,18 contra 12,12; BPM médio 120–169: 14,35 contra 14,43);
  - as calorias por hora são praticamente iguais entre tipos de treino (HIIT e yoga
    com 717 kcal/h; cardio e musculação com 724 kcal/h);
  - 0 valores ausentes e 0 linhas repetidas, o que é raro em dado coletado de verdade;
  - um R² de 98% com apenas quatro colunas, bom demais para dado de pessoas reais.
- A junção com o Compêndio confirmou de fora o que a fórmula mostrava de dentro: para
  o Compêndio, yoga gasta um terço do que gasta HIIT (2,3 contra 7,0 MET); na base, os
  dois gastam o mesmo (ver [Junção](#junção-aula-7)).
- Consequência: as respostas à pergunta norteadora descrevem **o gerador dos dados**,
  não praticantes reais. O pipeline continua valendo, mas qualquer conclusão sobre
  pessoas precisa de uma base real de treinos.
- Uma sessão por praticante e nenhuma coluna de tempo: não dá para acompanhar a
  evolução de ninguém.

### Compêndio
- A página e o PDF de janeiro de 2024 divergem em um código: `02280` (realidade
  virtual) tem 7,9 MET na página e 8,3 no PDF. Ficou o valor da página, que é a versão
  mais recente (atualizada em 05/04/2026). O código não é usado na junção.
- A própria fonte marca 4 valores como estimados, sem estudo publicado por trás
  (`02090`, `02135`, `02143`, `02160`). Eles viraram `met_estimado = True` na prata.
  Nenhum dos quatro é usado na junção.
- O MET do Compêndio é uma média para adultos, não o gasto medido de uma pessoa. O
  próprio artigo avisa que o valor não reflete o gasto individual preciso.

## Decisões de tratamento

### Academia (`transformar_gym_members.py`)
- Espaços removidos de nomes de coluna e de texto.
- Linhas idênticas repetidas: 0.
- `Gender` e `Workout_Type` tipadas como categoria **sem** ordem (nenhuma das duas tem
  escala natural); `treino_chave` criada ao lado para comparar e agrupar.
- `Experience_Level` (1, 2, 3) virou a categoria **com** ordem `experiencia`
  (`iniciante < intermediario < avancado`). É número, mas não se soma: 3 não é o triplo
  de 1. O número original continua na tabela.
- Dicionário de sinônimos do tipo de treino (`MAPA_TREINO`) declarado e vazio: a base
  vem padronizada, e escrever variante que ela não tem seria inventar defeito. Ele fica
  pronto para quando uma extração futura trouxer `hiit` ou `High Intensity`.
- A prata é salva em Parquet, que guarda o tipo de cada coluna: a categoria com ordem
  continua com ordem quando o arquivo é lido de novo.
- `sessao_id` (aula 9): número da sessão, de 1 a n, na ordem da bronze, depois de remover
  as repetidas. A fonte não tem identificador, e a tabela fato da Ouro precisa de uma
  chave (ver [Modelagem e carga](#modelagem-e-carga-aula-9)).
- Pendente: as checagens de qualidade da aula 5 (valor extremo por IQR e z-score,
  faixa válida por domínio) ainda não foram feitas nesta base.

### Compêndio (`transformar_compendio.py`)
- O código é lido **como texto** direto do CSV. Ele tem zero à esquerda: lido como
  número, `02000` vira `2000` e nunca mais casa com a academia — é o motivo "tipo
  diferente" de uma chave não casar.
- Colunas renomeadas para `codigo`, `met` e `atividade_compendio`; a descrição fica em
  inglês, como na fonte.
- Conferências: 0 códigos fora do formato de 5 dígitos, 0 ausentes, 0 repetidos (o
  código é chave única, e por isso o Compêndio pode ser o lado "um" da junção); 0 MET
  ausentes e 0 fora da faixa 0,9–25.
- `met_estimado` marca os 4 valores que a fonte avisa serem estimados.

## Junção (aula 7)

Enriquecer é acrescentar a um registro uma informação que já existe em outro lugar,
usando algo que os dois têm em comum. A sessão de academia diz **qual** treino foi
feito; o Compêndio diz **quanto** esse treino costuma gastar. As duas informações já
existiam, separadas: o Compêndio muda a cada atualização (1993, 2000, 2011, 2024) e a
sessão nasce a cada treino. A camada continua sendo a prata: sai mais uma tabela
tratada, `gym_members_enriquecida.parquet`, com informação das duas fontes.

### As quatro perguntas
1. **Quais duas tabelas, e qual o grão de cada uma?** Esquerda: `gym_members.parquet`,
   uma linha = uma sessão de um praticante. Direita: `compendio.parquet`, uma linha =
   uma atividade. Resultado: uma linha = uma sessão. O grão não muda, porque cada sessão
   casa com no máximo uma atividade.
2. **Por qual coluna?** `codigo_compendio` (academia) = `codigo` (Compêndio). A academia
   não tem código: ele sai do dicionário `MAPA_TREINO_COMPENDIO`, que traduz o tipo de
   treino para o código da atividade (motivo "grafia diferente": `Strength` e
   `Resistance (weight) training` são a mesma coisa escrita de jeitos diferentes). Os
   dois lados são texto.
3. **O que fazer com quem não casa?** `how="left"`: a sessão sem par continua na
   tabela, com MET ausente, e aparece na validação.
4. **Como sei que deu certo?** A previsão do passo 1 é comparada com a contagem do
   passo 3, e `validate="many_to_one"` faz o pandas levantar erro se o código repetir no
   Compêndio, em vez de devolver uma tabela inflada.

### Dicionário de mapeamento

| `Workout_Type` | Código | Atividade no Compêndio | MET |
|---|---|---|---|
| Cardio | 02000 | Aerobic, general | 7,3 |
| HIIT | 02210 | High intensity interval exercise, moderate effort | 7,0 |
| Strength | 02054 | Resistance (weight) training, multiple exercises, 8-15 reps at varied resistance | 3,5 |
| Yoga | 02175 | Yoga, General | 2,3 |

Critério, o mesmo para os quatro: a base não informa o esforço da sessão, então fica a
descrição mais geral do tipo; quando o Compêndio só separa por esforço (caso do HIIT),
fica *moderate effort*. Escolher *vigorous* (HIIT com 11,0 MET, musculação com 6,0)
seria inventar uma intensidade que a fonte não registrou. Efeito colateral documentado:
com esse critério, HIIT (7,0) fica um pouco abaixo de cardio geral (7,3).

### Resultado
Sessões juntadas ao Compêndio por `codigo_compendio = codigo`, com `how="left"` e
`validate="many_to_one"`.

Passo 1, antes de juntar (a previsão):
- Códigos só na academia: 0
- Códigos só no Compêndio: 82
- Códigos nos dois: 4
- Sessões sem código (tipo de treino fora do dicionário): 0

Passo 3, depois de juntar (a conta que precisa fechar):
- Linhas na academia: 973
- Linhas no resultado: 973
- Sem par no Compêndio: 0

### Quem não casou
- **0 sessões sem par.** Os quatro tipos de treino da base estão no dicionário e os
  quatro códigos existem no Compêndio. Se uma extração futura trouxer um tipo novo
  (`Pilates`, por exemplo), ele fica sem código, aparece como "sem par" na validação e
  não some: basta acrescentar uma linha ao dicionário (`02105`, *Pilates, general*).
- **82 atividades do Compêndio sem nenhuma sessão.** São universos diferentes: o
  Compêndio cobre toda a seção de condicionamento físico (remo, elíptico, pular corda,
  zumba, pilates, realidade virtual…), e a academia registra só quatro tipos de treino.
  Não se resolve, documenta-se. Como a junção parte da academia (`left`), essas
  atividades não entram no resultado, e não deveriam: elas não são sessões.

### O problema em aberto se fecha
Antes da junção, a base mostrava as mesmas calorias por hora para todos os treinos, mas
não havia nenhuma coluna para dizer se isso estava errado. Com o MET ao lado, dá para
comparar com o que o Compêndio espera para o mesmo peso:

| Treino | Sessões | MET | kcal/h na base | kcal/h esperada (MET × peso) | base ÷ esperada |
|---|---|---|---|---|---|
| Cardio | 255 | 7,3 | 723,8 | 546,3 | 1,32 |
| HIIT | 221 | 7,0 | 716,5 | 522,4 | 1,37 |
| Strength | 258 | 3,5 | 724,0 | 252,7 | 2,87 |
| Yoga | 239 | 2,3 | 716,5 | 169,9 | 4,22 |

A base dá à yoga 4,2 vezes o que o Compêndio espera, e à musculação quase 3 vezes; nos
treinos aeróbicos a diferença cai para 1,3. É a confirmação, por uma fonte
independente, de que a fórmula da base ignora o tipo de treino.

## Atributos derivados

Um atributo derivado é uma coluna nova, calculada a partir das que já existem, que
responde melhor à pergunta do que qualquer uma delas sozinha. A fonte publicou o que
ela achou útil; ninguém lá sabia o que este projeto queria perguntar.

Critério: uma frase explica por que a coluna ajuda a responder a pergunta norteadora,
ela não repete informação que já existe em outra coluna, e o cálculo está em uma
função com nome que diz o que ela faz.

### `calorias_por_hora` (aula 6)
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

### `calorias_met` (aula 7, só existe depois da junção)
`met × Weight (kg) × Session_Duration (hours)`, em kcal: a estimativa do Compêndio para
a mesma sessão. Antes da junção não dava para calcular, porque o MET estava na outra
tabela.

Serve à pergunta norteadora porque usa duas características do praticante — o peso e o
tipo de treino — que o Compêndio diz pesarem no gasto e que a fórmula da base ignora;
colocar as duas estimativas lado a lado mostra quanto da resposta da base vem do
gerador dos dados, e não da fisiologia.

Faixa observada: 58,8 a 1325,9 kcal por sessão, média 464,4 (a base dá média de 905).
Quanto cada coluna explica das calorias da base (R² de uma reta):

- só a duração: 82,5%;
- `calorias_met` (duração × peso × MET): 20,4%.

Acrescentar peso e tipo de treino **piora** a explicação, de 82,5% para 20,4%: as
calorias da base não respondem às duas coisas que, pelo Compêndio, mais deveriam
mudá-las.

Ao lado dela, `razao_base_met = Calories_Burned / calorias_met` diz, sessão a sessão,
quantas vezes a base dá o que o Compêndio espera (1 seria concordância). Mediana 2,21;
vai de 0,74 a 7,88.

## Proveniência
- `dados/bronze/gym_members/proveniencia.json` — de onde veio (dataset do Kaggle), qual
  era o arquivo original, qual é o arquivo na bronze e quando foi extraído.
- `dados/bronze/compendio/proveniencia.json` — página e PDF de conferência, citação do
  artigo, como a tabela foi copiada, divergência página × PDF, códigos estimados pela
  fonte e data de extração.
- `dados/prata/proveniencia.jsonl` — uma linha por execução de cada script de
  transformação, com as decisões tomadas e os números reais daquela execução, não fixos
  no texto. A linha do `enriquecer_gym_members.py` guarda o dicionário de mapeamento, a
  previsão do passo 1, a contagem do passo 3 e a tabela por tipo de treino.

## Pipeline (aula 8)

Até a aula 7 o projeto eram oito scripts soltos. A ordem existia só na cabeça de quem
escreveu, o mesmo caminho (`Path("dados/prata")`) estava escrito em cinco arquivos e
cada script falava por `print`. Nenhuma etapa nova de dado entrou: mudou a forma.

### `config.py`
Caminhos, identificação das fontes e as faixas de plausibilidade (kcal/h e MET) moram
em um lugar só. `RAIZ` é calculada a partir do próprio arquivo, e por isso os scripts
acham a pasta `dados` de qualquer lugar de onde forem rodados.

O teste para uma linha ir para o config: quem rodar o projeto em outra máquina, ou com
outra extração, precisa editar essa linha? Os dicionários de mapeamento (`MAPA_TREINO`,
`MAPA_TREINO_COMPENDIO`) **não** foram para o config: são decisões sobre o significado
do dado, específicas de cada fonte, e ficam no script que as usa. O token do Kaggle
também não vai para lá: o config vai para o GitHub.

### Quem importa quem
```
pipeline.py
   └─ ingerir · transformar_gym_members · transformar_compendio · enriquecer_gym_members · carga
         └─ limpeza · juncao            (não importam nenhuma etapa)
               config                   (não importa ninguém)
```
A seta nunca volta. `limpeza` e `juncao` nem importam o config: só pedem um logger com
o próprio nome, e quem decide se a mensagem aparece é quem roda.

### Log no lugar do `print`
`config.configurar_log()` manda cada mensagem para a tela e para `pipeline.log` (no
`.gitignore`), com data, hora, nível e o módulo que falou. O carimbo leva a data além da
hora, porque o arquivo acumula execuções. Critério dos níveis:

- `INFO` — o que se vai querer saber amanhã: registros lidos e salvos, a previsão e a
  contagem da junção, o R² das calorias.
- `WARNING` — estranho, mas seguiu: linhas sem par na junção, chave repetida, valor fora
  da faixa plausível, download do Kaggle que falhou.
- `DEBUG` — só para investigar: colunas lidas, tabelas intermediárias, estatísticas.
- `ERROR` — não deu para continuar: a etapa falhou e o pipeline parou.

Uma consequência visível: com zero defeitos (o caso desta extração), as linhas de aviso
simplesmente não aparecem. O que aparece em amarelo é o que precisa de atenção.

### Diante do erro
- **Etapa que falha para o pipeline.** `executar()` grava o rastro inteiro com
  `log.exception` e devolve o erro (`raise`): seguir para a etapa seguinte com dado pela
  metade seria o pipeline mentir que deu certo.
- **Tratar e decidir, uma vez.** Se o download do Kaggle falhar (sem rede, token
  vencido) e a bronze já tiver uma extração, o pipeline segue com a extração anterior e
  registra um `WARNING` com o nome do arquivo usado. A bronze guarda cada extração com a
  data no nome, então nada se perde; se ela estiver vazia, o erro sobe.

### Retomar do meio
`python src/pipeline.py enriquecimento` pula as etapas anteriores e roda daí em diante.
Consertou uma linha da junção? Não precisa baixar do Kaggle de novo. Nome de etapa
errado não roda nada e lista as etapas que existem.

```
2026-11-19 16:11:28 INFO pipeline: etapa ingestao: inicio
2026-11-19 16:11:28 INFO ingerir: compendio: sem ingestao automatica, usando compendio_condicionamento_20261022.csv
2026-11-19 16:11:28 INFO pipeline: etapa ingestao: fim em 0s
2026-11-19 16:11:28 INFO pipeline: etapa transformacao: inicio
2026-11-19 16:11:28 INFO transformar_gym_members: academia: 973 linhas na bronze -> 973 na prata
2026-11-19 16:11:28 INFO transformar_compendio: compendio: 86 linhas na bronze -> 86 na prata
...
2026-11-19 16:11:33 INFO dbt: Done. PASS=32 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=32
2026-11-19 16:11:33 INFO pipeline: etapa modelagem: fim em 5s
2026-11-19 16:11:33 INFO pipeline: pipeline concluido
```

### O que este pipeline não faz
Roda quando alguém manda, uma etapa por vez, e quem descobre a falha é quem lê o log.
Agendar, tentar de novo sozinho e avisar alguém é trabalho de agendador ou orquestrador
(Agendador de Tarefas do Windows, GitHub Actions, Airflow…). Para uma base que muda uma
vez por extração, o degrau de agora basta.

## Modelagem e carga (aula 9)

Modelar não é sobre o dado que se tem: é sobre as perguntas que vão ser feitas a ele.
A pergunta norteadora pede para comparar calorias entre **características do
praticante** e entre **tipos de treino**. As características descrevem quem treinou, o
treino descreve o que foi feito, e as calorias são o que se mede.

### As três respostas, antes de qualquer SQL
1. **Quais tabelas?** Uma fato e duas dimensões (esquema estrela).
2. **Qual o grão de cada uma?**
   - `fato_sessao`: **uma linha é uma sessão de treino de um praticante.**
   - `dim_praticante`: uma linha por praticante.
   - `dim_treino`: uma linha por tipo de treino.
3. **Como elas se ligam?** `fato_sessao.praticante_id → dim_praticante.praticante_id` e
   `fato_sessao.treino_id → dim_treino.treino_id`.

```
   dim_praticante                                  dim_treino
   praticante_id ──┐                         ┌── treino_id
   genero          │       fato_sessao       │   tipo_treino
   idade           │       sessao_id         │   codigo_compendio
   peso_kg, imc    └────── praticante_id     │   atividade_compendio
   gordura_pct             treino_id ────────┘   met, met_estimado
   bpm_repouso             duracao_h
   agua_litros             calorias_base
   treinos_por_semana      bpm_medio, bpm_max
   experiencia             calorias_por_hora
   (973 linhas)            calorias_met, razao_base_met     (4 linhas)
                           (973 linhas)
```

### Fato ou dimensão, coluna por coluna
O teste da aula: número que se soma ou se tira média é fato; palavra pela qual se
agrupa ou filtra é dimensão. A divisão seguiu os quatro grupos de colunas da fonte:

- **Sessão** (duração, calorias, BPM médio e máximo na sessão) → `fato_sessao`, junto
  com os atributos derivados das aulas 6 e 7, que são medidas da sessão.
- **Perfil, hábitos e BPM em repouso** → `dim_praticante`. Peso, idade e % de gordura
  são números, mas aqui fazem papel de característica de quem treinou: é por eles que a
  pergunta compara.
- **Tipo de treino e o que o Compêndio diz dele** → `dim_treino`. É o cadastro da
  junção da aula 7 virando dimensão.

### A chave que a fonte não tinha
A base do Kaggle não traz identificador nenhum, nem de sessão nem de pessoa. A prata
ganhou `sessao_id` (1 a n, na ordem da bronze, em `transformar_gym_members.py`): o número
nasce na prata, e não na Ouro, porque precisa atravessar a junção junto com a linha. A
fonte registra uma sessão por praticante, então o praticante herda o número da sessão.
Duas consequências, documentadas e não escondidas:

- o número vale dentro de uma extração; uma extração nova com outra ordem numera de
  outro jeito;
- se duas linhas forem da mesma pessoa, não há como saber. Se uma extração futura
  trouxer um id de pessoa, só a `dim_praticante` muda.

### Banco: DuckDB
Banco embutido: uma biblioteca (`pip install duckdb`), sem servidor, sem senha, sem
porta. O banco inteiro é `dados/ouro/projeto.duckdb` (no `.gitignore`, porque é
reconstruível), e apagar o arquivo é um jeito legítimo de recomeçar. Ele lê os Parquet
da prata direto, com os tipos (o código do Compêndio chega como texto, com o zero à
esquerda).

A camada deixa de ser pasta e vira esquema: `prata.*` entra como está (pelo
`carga.py`) e `ouro.*` nasce dentro do banco, em SQL. Os nomes da Ouro são de negócio
(`calorias_base`, `peso_kg`), não os da fonte (`Calories_Burned`, `"Weight (kg)"`).

### A tabela achatada virou view
`gym_members_enriquecida.parquet`, da aula 7, ganhou três destinos: é a entrada da fato
e das duas dimensões; o filtro `codigo IS NOT NULL` (sessão cujo treino achou par no
Compêndio) virou o filtro de integridade da fato e da `dim_treino`; e a tabela achatada
voltou como `ouro.vw_sessao_completa`, uma view montada a partir da estrela. Corrigir o
MET de um treino é uma linha na `dim_treino`, e a view já sai certa.

### Conferência (ainda em Python, na aula 9)
Todas precisam dar zero, e deram: sessões repetidas na fato 0, treinos repetidos na
`dim_treino` 0, fatos sem treino 0, fatos sem praticante 0, sessões da prata fora da
fato 0. Contagens: `dim_treino` 4, `dim_praticante` 973, `fato_sessao` 973,
`vw_sessao_completa` 973.

Detalhe de versão: no DuckDB 2.0, ler só a primeira linha com `fetchone()` deixa a
conexão ocupada e o comando seguinte falha (*connection has an unfinished result*). O
`um_valor()` do `carga.py` usa `fetchall()[0][0]`.

## Transformação declarativa: dbt (aula 10)

O `carga.py` fazia duas coisas de natureza diferente: ler arquivo para dentro do banco
(continua em Python) e construir a Ouro com SQL dentro de string (passou para o dbt).
`construir_ouro()` ficou no arquivo, fora do `main()`, para comparar.

```
ecox14/
  dbt_project.yml                nome, pastas, perfil e as vars da faixa de kcal/h
  profiles.yml                   como conectar no banco
  models/sources.yml             onde o grafo começa: as tabelas do esquema prata
  models/dim_treino.sql          os mesmos SELECT do carga.py,
  models/dim_praticante.sql      sem o CREATE TABLE em volta
  models/fato_sessao.sql
  models/vw_sessao_completa.sql  a view: {{ config(materialized='view') }}
  models/schema.yml              documentação e testes (aula 11)
  tests/                         testes escritos à mão (aula 11)
```

- `{{ source('prata', ...) }}` aponta para tabela que o dbt não faz; `{{ ref(...) }}`
  aponta para outro modelo e cria a dependência. Só a view usa `ref`, e por isso o dbt
  a constrói por último. A ordem nunca foi escrita.
- **`profiles.yml` dentro do projeto.** A aula o coloca em `C:\Users\...\.dbt\` com o
  caminho completo do banco. Aqui ele fica em `ecox14/`, com o caminho relativo
  `../dados/ouro/projeto.duckdb`: o dbt procura o perfil primeiro na pasta de onde é
  rodado, e o projeto roda em qualquer máquina sem editar nada. Não tem segredo (o
  DuckDB não tem senha), então pode ir para o GitHub. `dbt debug` mostra qual arquivo
  foi lido.
- **O último `None` virou função.** A etapa *modelagem* do `pipeline.py` roda o dbt de
  dentro de `ecox14/`. O dbt é procurado ao lado do Python que está rodando, então
  funciona mesmo com a `.venv` desativada, desde que se use o Python dela.

**A migração não mudou o resultado:** as quatro tabelas construídas pelo dbt foram
comparadas linha a linha com as do `construir_ouro()` e saíram idênticas (4, 973, 973 e
973 linhas).

```
cd ecox14
dbt run                        # constrói as 4
dbt run --select dim_treino+   # só a dim_treino e o que depende dela (a view)
```

## Testes, documentação e entrega (aula 11)

### O `conferir()` virou teste
Um teste é uma consulta que precisa devolver zero linhas; se devolver alguma, ele
falha. A etapa *modelagem* roda `dbt build` (e não só `dbt run`): ele testa as origens,
constrói cada modelo e o testa logo em seguida, na ordem do grafo. Se um teste falha, o
que depende do modelo nem é construído, e o pipeline para com `ERROR`.

| Conferência da aula 9 | Virou |
|---|---|
| sessão repetida na fato (o grão) | `unique` + `not_null` em `fato_sessao.sessao_id` |
| treino repetido na dimensão | `unique` em `dim_treino.treino_id` |
| fato sem treino / sem praticante | `relationships` nas duas chaves da fato |
| sessões da prata fora da fato | teste escrito à mão: `tests/sessoes_fora_da_fato.sql` |

Na aula, o teste do grão é escrito à mão porque a chave é composta (país + ano). Aqui a
chave da fato é uma coluna só, e o teste pronto `unique` cobre o grão. Os testes à mão
ficaram para o que nenhum teste pronto cobre:

- `sessoes_fora_da_fato` — a contagem prata = fato, a conta "antes = depois" da aula 7;
- `vw_sessao_completa_sem_perda` — a view tem tantas linhas quanto a fato (o join não
  perdeu nem duplicou sessão);
- `calorias_por_hora_plausivel` — sessões fora de 200–1500 kcal/h, com
  `severity='warn'`: a decisão da aula 6 foi **sinalizar, não remover**, então ele avisa
  e o pipeline segue. A faixa está nas `vars` do `dbt_project.yml`, com os mesmos números
  do `config.py`.

Além disso: `accepted_values` em tipo de treino, gênero e nível de experiência,
`not_null` nas medidas principais, e testes nas origens (`sessao_id` e código do
Compêndio únicos), que barram dado de entrada errado antes de qualquer transformação.

Resultado: **32 de 32** (4 modelos e 28 testes), `WARN=0`. Foi conferido que os testes
pegam o erro de verdade: tirando a yoga da `dim_treino`, o `relationships` da fato
falhou com 239 linhas (as sessões de yoga), a view e o teste dela foram pulados, e o
pipeline parou na etapa *modelagem*. Para ver as linhas de um teste que falhou:

```
cd ecox14
dbt test --select calorias_por_hora_plausivel --store-failures
```

### Documentação
Cada modelo e cada coluna da Ouro tem descrição no `schema.yml`, ao lado do teste. O
site sai do próprio código, com o grafo dos modelos:

```
cd ecox14
dbt docs generate
dbt docs serve
```

### Ver o dado
Para olhar as linhas, a interface do DuckDB: baixe o pacote de linha de comando em
duckdb.org (Windows), descompacte o `duckdb.exe` na raiz do projeto (já está no
`.gitignore`) e rode, com o pipeline e o painel fechados:

```
.\duckdb.exe -ui dados/ouro/projeto.duckdb
```

### O painel
`streamlit run dashboard/painel.py`. Três blocos, todos filtráveis por tipo de treino,
gênero e experiência:

1. **A pergunta norteadora:** quanto cada característica explica, sozinha, das calorias
   da base (R² de uma reta).
2. **Base × Compêndio:** kcal/h que a base dá contra a que o Compêndio espera (MET ×
   peso), por tipo de treino.
3. **As sessões do recorte**, uma por linha.

O rodapé diz de onde veio cada número (fonte e data de extração, lidas da proveniência
da bronze) e avisa que a base é sintética.

Onde mora o SQL: o que **cria** tabela está no dbt, versionado e testado; o que **lê**
está em `dashboard/consultas.py`, uma função por pergunta; a tela (`painel.py`) não tem
SQL. Valor que vem da tela entra como parâmetro (`?`), nunca concatenado. O nome das
colunas no R² é a única parte montada no texto, e vem de uma lista fixa no código, nunca
da tela. A conexão é `read_only` e abre e fecha a cada consulta, então o painel aberto
não segura o arquivo e o pipeline consegue gravar.

O que o painel mostra com esta extração (sem filtro):

| Característica | R² com as calorias da base |
|---|---|
| Duração da sessão | 82,5% |
| Nível de experiência | 48,2% |
| % de gordura | 35,7% |
| Treinos por semana | 33,2% |
| Água por dia | 12,7% |
| BPM médio na sessão | 11,5% |
| Idade | 2,4% |
| Peso | 0,9% |
| MET do treino (Compêndio) | 0,0% |

Experiência, gordura e frequência aparecem alto sem entrar na fórmula da base: elas
andam junto com a duração (o nível de experiência sozinho explica 58,5% da duração). Os
avançados treinam 1,76 h por sessão, e os iniciantes, 1,01 h, mas as calorias **por
hora** são as mesmas nos três níveis (719 a 722 kcal/h). E o MET do treino, que pelo
Compêndio deveria pesar muito, explica 0%.

### Governança
- **De onde veio este número?** Proveniência da bronze (fonte, arquivo, data), da prata
  (`proveniencia.jsonl`, uma linha por execução, com as decisões e os números reais) e o
  rodapé do painel. O caminho de qualquer número da Ouro pode ser reconstruído:
  `pipeline.log` → modelo dbt → prata → bronze.
- **Quem pode vê-lo?** O banco e o painel rodam só na máquina de quem executa. O
  repositório não leva dado: prata e Ouro estão no `.gitignore`.
- **E se estiver errado?** Os testes param o pipeline antes de a Ouro chegar ao painel,
  e o aviso de base sintética vai junto com cada número.

**Dado pessoal.** A base tem idade, gênero, peso, % de gordura e frequência cardíaca de
cada praticante. Ela é sintética e não tem identificador de pessoa, então não identifica
ninguém. Se fosse de uma academia de verdade, seria dado pessoal sensível (dado de
saúde, LGPD, art. 5º, II), e o projeto precisaria de outra postura: coletar só o que a
pergunta usa, dizer para que o dado serve, definir prazo de descarte, trocar qualquer identificador real
por um número sem significado (como o `sessao_id`) e controlar quem acessa o banco e o
painel. Nada disso é tecnologia: é decisão registrada.

## Apresentação
- `apresentacao/apresentacao.html` — 10 telas interativas que abrem offline no
  navegador, com os dados da prata embutidos (setas do teclado trocam de tela).
- `apresentacao/roteiro_apresentacao.pdf` — roteiro de fala de 10 minutos, com
  perguntas prováveis e números de bolso. O `.tex` ao lado gera o PDF (xelatex).
- As duas foram feitas antes da aula 7: não cobrem o enriquecimento com o Compêndio nem
  o pipeline, o banco, o dbt e o painel (aulas 8 a 11).
