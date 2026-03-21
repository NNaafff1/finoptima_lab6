from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.db.models import Sum
from django.utils import timezone
from .models import Transaction, Category, Recommendation


def init_categories():
    """Создаёт базовые категории, если их нет"""
    if Category.objects.count() == 0:
        categories_data = [
            ('Зарплата', 'income'),
            ('Фриланс', 'income'),
            ('Инвестиции', 'income'),
            ('Еда', 'expense'),
            ('Транспорт', 'expense'),
            ('Жильё', 'expense'),
            ('Развлечения', 'expense'),
            ('Покупки', 'expense'),
        ]
        
        for name, type_ in categories_data:
            Category.objects.create(name=name, type=type_)


@login_required
def dashboard(request):
    """Главная страница с финансовой статистикой"""
    # Инициализация категорий
    init_categories()
    
    now = timezone.now()
    first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    transactions = Transaction.objects.filter(
        user=request.user, 
        date__gte=first_day
    ).order_by('-date')
    
    income = transactions.filter(category__type='income').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    expense = transactions.filter(category__type='expense').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    balance = income - expense
    
    context = {
        'balance': balance,
        'income': income,
        'expense': expense,
        'recent_transactions': transactions[:5],
    }
    
    return render(request, 'core/dashboard.html', context)


@login_required
def add_transaction(request):
    """Добавление новой транзакции"""
    categories = Category.objects.all()
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        category_id = request.POST.get('category')
        date = request.POST.get('date')
        description = request.POST.get('description')
        
        category = Category.objects.get(id=category_id)
        
        Transaction.objects.create(
            user=request.user,
            amount=amount,
            category=category,
            date=date,
            description=description
        )
        
        return redirect('dashboard')
    
    return render(request, 'core/add_transaction.html', {'categories': categories})


@login_required
def get_recommendation(request):
    """Генерация финансовой рекомендации"""
    now = timezone.now()
    first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    transactions = Transaction.objects.filter(
        user=request.user, 
        date__gte=first_day
    )
    
    total_income = transactions.filter(category__type='income').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    total_expense = transactions.filter(category__type='expense').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    advice_text = ""
    
    if total_income == 0:
        advice_text = "Добавьте информацию о ваших доходах для получения рекомендаций."
    elif total_expense == 0:
        advice_text = "У вас пока нет расходов в этом месяце. Отлично!"
    else:
        expense_ratio = (total_expense / total_income) * 100
        
        if expense_ratio > 90:
            advice_text = f"⚠️ Внимание! Вы потратили {expense_ratio:.1f}% от дохода. Сократите расходы!"
        elif expense_ratio > 70:
            advice_text = f"Расходы составляют {expense_ratio:.1f}% от дохода. Отложите 10-15% на сбережения."
        elif expense_ratio > 50:
            advice_text = f"Хороший баланс! Расходы {expense_ratio:.1f}% от дохода."
        else:
            advice_text = f"Отлично! Вы тратите {expense_ratio:.1f}% от дохода. Подумайте об инвестициях."
    
    Recommendation.objects.create(
        user=request.user,
        text=advice_text
    )
    
    return render(request, 'core/recommendation.html', {'advice': advice_text})