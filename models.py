from django.db import models

class City(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    state = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = 'Cities'
        ordering = ['name']

    def __str__(self):
        return f"{self.name}, {self.state}"

class Theater(models.Model):
    name = models.CharField(max_length=150, db_index=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='theaters', db_index=True)
    address = models.TextField()
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['city']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.city.name})"

class Screen(models.Model):
    SCREEN_TYPES = [
        ('2D', 'Standard 2D'),
        ('3D', 'RealD 3D'),
        ('IMAX', 'IMAX 3D'),
        ('4DX', '4DX Motion'),
    ]

    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='screens')
    name = models.CharField(max_length=50) # e.g. Screen 1, Audi 2
    screen_type = models.CharField(max_length=10, choices=SCREEN_TYPES, default='2D')
    total_seats = models.IntegerField(default=120)

    def __str__(self):
        return f"{self.theater.name} - {self.name} ({self.screen_type})"

class Seat(models.Model):
    SEAT_TYPES = [
        ('REGULAR', 'Regular'),
        ('PREMIUM', 'Premium'),
        ('VIP', 'VIP Recliner'),
    ]

    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name='seats')
    row = models.CharField(max_length=5) # A, B, C...
    number = models.IntegerField() # 1, 2, 3...
    seat_type = models.CharField(max_length=15, choices=SEAT_TYPES, default='REGULAR')
    base_price = models.DecimalField(max_digits=8, decimal_places=2, default=250.00)

    class Meta:
        unique_together = ('screen', 'row', 'number')
        ordering = ['row', 'number']

    @property
    def seat_label(self):
        return f"{self.row}{self.number}"

    def __str__(self):
        return f"{self.screen.theater.name} - {self.screen.name} - Seat {self.seat_label}"
