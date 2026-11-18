# API de Atividades da Mergington High School

Uma aplicação FastAPI super simples que permite aos estudantes visualizar e se inscrever em atividades extracurriculares.

## Funcionalidades

- Visualizar todas as atividades extracurriculares disponíveis
- Professores autenticados podem gerenciar inscrições de estudantes

## Primeiros Passos

1. Instale as dependências:

   ```
   pip install fastapi uvicorn
   ```

2. Configure as credenciais de professor e a chave de assinatura da sessão no ambiente antes de iniciar a aplicação:

   ```
   export TEACHER_USERNAME=teacher
   export TEACHER_PASSWORD='use-a-strong-password'
   export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
   ```

   Para desenvolvimento local via HTTP, defina `SESSION_COOKIE_SECURE=false`. Em produção, use HTTPS e mantenha essa opção habilitada (o padrão).

3. Execute a aplicação:

   ```
   .venv/bin/uvicorn src.app:app --host 127.0.0.1 --port 8000
   ```

4. Abra seu navegador e vá para:
   - Documentação da API: http://localhost:8000/docs
   - Documentação alternativa: http://localhost:8000/redoc

## Endpoints da API

| Método | Endpoint                                                          | Descrição                                                           |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Obter todas as atividades com seus detalhes e contagem atual de participantes |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Inscrever estudante (somente professor autenticado)                 |
| POST   | `/auth/login`                                                      | Iniciar uma sessão de professor                                     |
| POST   | `/auth/logout`                                                     | Encerrar a sessão de professor                                      |
| GET    | `/auth/status`                                                     | Verificar o estado da sessão                                        |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Cancelar inscrição (somente professor autenticado)               |

## Modelo de Dados

A aplicação usa um modelo de dados simples com identificadores significativos:

1. **Atividades** - Usa o nome da atividade como identificador:

   - Descrição
   - Cronograma
   - Número máximo de participantes permitidos
   - Lista de emails de estudantes que estão inscritos

2. **Estudantes** - Usa email como identificador:
   - Nome
   - Nível da série

Todos os dados são armazenados na memória, o que significa que os dados serão resetados quando o servidor reiniciar.
