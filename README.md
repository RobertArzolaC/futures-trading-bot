# Knowing Labs Lis

## Configuration Development Environment

1. **Create the virtual environment:**
   ```bash
   python3 -m venv venv
   ```

2. **Activate Env**
   ```bash
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements/development.txt
   ```

4. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create Super User**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run Server**
   ```bash
   python manage.py runserver
   ```

## Coverage

1. **Run Tests with coverage**
   ```bash
   coverage run manage.py test
   ```

2. **Generate report**
   ```bash
   coverage report -m
   ```
