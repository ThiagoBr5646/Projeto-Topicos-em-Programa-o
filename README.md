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
- `dados/prata` — dado limpo e padronizado, inclusive a tabela enriquecida
- `dados/ouro` — dado modelado, pronto para análise
- `src` — scripts do pipeline
- `relatorios` — relatório de perfilamento (gerado, fica fora do git)
- `apresentacao` — apresentação interativa e roteiro de fala

### Scripts

| Script | O que faz |
|---|---|
| `src/ingerir.py` | Baixa a base do Kaggle e guarda na bronze, com a data no nome e a proveniência |
| `src/ler_dados.py` | Leitura rápida da bronze: abre o CSV mais recente e mostra o formato |
| `src/explorar.py` | Gera o relatório de perfilamento da base |
| `src/limpeza.py` | **Módulo** com as funções de limpeza que servem a qualquer fonte |
| `src/juncao.py` | **Módulo** com as funções de junção que servem a qualquer par de tabelas |
| `src/transformar_gym_members.py` | Academia: bronze → prata |
| `src/transformar_compendio.py` | Compêndio: bronze → prata |
| `src/enriquecer_gym_members.py` | Junta academia e Compêndio (continua na prata) |

`src/limpeza.py` e `src/juncao.py` não são executáveis: eles são importados. O critério
para uma função morar neles é um só — se a função menciona o nome da fonte (o tipo de
treino da academia, o código do Compêndio), ela fica no script da fonte; se não
menciona, é do módulo e serve para qualquer base que entrar no projeto.

Ordem de execução, sempre a partir da raiz do projeto e **com a `.venv` ativada**
(o Python global não tem `pyarrow`, e sem ele `to_parquet` falha):

```
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python src/ingerir.py
python src/explorar.py
python src/transformar_gym_members.py
python src/transformar_compendio.py
python src/enriquecer_gym_members.py
```

O `ingerir.py` precisa de um token do Kaggle configurado. O arquivo `kaggle.json`
está no `.gitignore` e nunca vai para o repositório. O Compêndio não tem script de
ingestão: a página é pública, mas não tem API nem arquivo para baixar, e a tabela foi
copiada para CSV (detalhes em [Fontes de dados](#fontes-de-dados)).

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

## Apresentação
- `apresentacao/apresentacao.html` — 10 telas interativas que abrem offline no
  navegador, com os dados da prata embutidos (setas do teclado trocam de tela).
- `apresentacao/roteiro_apresentacao.pdf` — roteiro de fala de 10 minutos, com
  perguntas prováveis e números de bolso. O `.tex` ao lado gera o PDF (xelatex).
