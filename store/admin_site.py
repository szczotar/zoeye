from django.contrib.admin import AdminSite
from django.db.models import Count
from .models import PageView
import datetime

class MyAdminSite(AdminSite):
    def index(self, request, extra_context=None):
        # Pobierz dane do statystyk
        today = datetime.date.today()
        
        views_today = PageView.objects.filter(timestamp__date=today).count()
        unique_visitors_today = PageView.objects.filter(timestamp__date=today).values('session_key').distinct().count()
        total_views = PageView.objects.count()
        total_unique_visitors = PageView.objects.values('session_key').distinct().count()
        
        top_pages_today = PageView.objects.filter(timestamp__date=today).values('path').annotate(count=Count('id')).order_by('-count')[:10]

        # Przygotuj kontekst
        stats_context = {
            'stats': {
                'views_today': views_today,
                'unique_visitors_today': unique_visitors_today,
                'total_views': total_views,
                'total_unique_visitors': total_unique_visitors,
            },
            'top_pages': top_pages_today,
        }
        
        # Połącz nasz kontekst z istniejącym
        if extra_context:
            stats_context.update(extra_context)
        
        return super().index(request, stats_context)

# Stwórz instancję naszej niestandardowej strony admina
site = MyAdminSite()