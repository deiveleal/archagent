# Portal de pedidos

Precisamos modelar o portal de pedidos da loja.

- O cliente acessa o **Portal Web** para registrar pedidos.
- O Portal Web chama a **API de Pedidos** por REST.
- A API de Pedidos grava os pedidos no **PostgreSQL**.
- A API de Pedidos roda num **cluster Kubernetes** na AWS.
- A equipe de Atendimento acompanha os pedidos pelo **Backoffice**, que também consulta a API de Pedidos.

Decisão: o PostgreSQL será gerenciado (Amazon RDS).
