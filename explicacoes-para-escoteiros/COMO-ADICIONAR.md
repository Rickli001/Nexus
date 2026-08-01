# Como adicionar uma nova explicação

O site é organizado assim: a página inicial (`index.html`) é um catálogo com
todas as explicações, e cada tema tem a sua própria página (por exemplo,
`bullying.html`). Para publicar um novo tema, são só dois passos:

## 1. Crie a página do tema

1. Copie o arquivo `modelo.html` e dê a ele o nome do tema, em letras
   minúsculas e com hífens no lugar de espaços. Exemplos:
   - `nos-e-amarras.html`
   - `primeiros-socorros.html`
2. Abra o arquivo copiado e siga os comentários (`<!-- ... -->`) que estão
   dentro dele: troque o título, o nome das abas e o conteúdo das seções.
3. Regras das abas:
   - Cada botão `<button class="tab-btn" data-tab="...">` abre a `<section>`
     cujo `id` é igual ao valor de `data-tab`.
   - A primeira seção deve ter `class="tab-panel active"`; as outras, apenas
     `class="tab-panel"`.
   - Pode adicionar ou remover abas à vontade — o `script.js` cuida do resto.

## 2. Adicione o tema ao catálogo

Abra o `index.html`, copie um bloco de cartão existente e ajuste o link,
o título e a descrição:

```html
<a class="card card-tema" href="nos-e-amarras.html">
  <h3>Nós e Amarras</h3>
  <p>Descrição curta do que a pessoa vai encontrar nesta explicação.</p>
  <span class="ler-mais">Ler explicação →</span>
</a>
```

Cole o bloco dentro da `<div class="catalogo">`, antes do cartão "Em breve".
Pronto: salve os dois arquivos e a nova explicação está no ar.

## Dicas de estilo

- Escreva com linguagem simples e direta — frases curtas, exemplos concretos.
- `class="card destaque"` cria uma caixa de destaque (borda amarela).
- `class="card atencao"` cria uma caixa de alerta (borda vermelha).
- `class="dica"` cria uma nota com fundo amarelo claro.
- `class="citacao"` formata citações com fundo verde claro.
- A tabela de comparação e a linha do tempo usadas em `bullying.html` também
  podem ser copiadas de lá, se o tema precisar.
