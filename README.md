A simple example of project on cloud payments, fastapi, aiogram, polling

## Quick manual start of polling mode

1. Install Dependencies
`poetry install`
2. Create .env from template.env and fill in all fields
3. Run database container:
`docker run --name pg-container -e POSTGRES_DB=payment_db -e POSTGRES_USER=payment_user -e POSTGRES_PASSWORD=payment_password -p 5432:5432 -d postgres:15`
4. Run `pooling_mode.py`
5. Type `/start` or `/get_payment` to the bot

## Quick Docker start of polling mode

1. Create .env from template.env and fill in all fields
2. Run docker-compose: `docker-compose up --build`
3. Type `/start` or `/get_payment` to the bot