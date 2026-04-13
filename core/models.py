from django.db import models
from django.contrib.auth.models import User
import json


class Dataset(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='datasets')
    name = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to='datasets/')
    file_type = models.CharField(max_length=20, default='csv')  # csv, xlsx, sav
    rows = models.IntegerField(default=0)
    columns = models.IntegerField(default=0)
    column_info = models.TextField(default='[]')  # JSON: [{name, type, label}]
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    def get_column_info(self):
        return json.loads(self.column_info)

    def set_column_info(self, info):
        self.column_info = json.dumps(info)


class AnalysisResult(models.Model):
    ANALYSIS_TYPES = [
        ('descriptive', 'Deskriptif'),
        ('frequencies', 'Frekuensi'),
        ('crosstab', 'Crosstab'),
        ('ttest_independent', 'T-Test Independen'),
        ('ttest_onesample', 'T-Test 1 Sampel'),
        ('ttest_paired', 'T-Test Berpasangan'),
        ('anova_oneway', 'ANOVA Satu Arah'),
        ('anova_twoway', 'ANOVA Dua Arah'),
        ('manova', 'MANOVA'),
        ('correlation_pearson', 'Korelasi Pearson'),
        ('correlation_spearman', 'Korelasi Spearman'),
        ('regression_linear', 'Regresi Linear'),
        ('regression_logistic', 'Regresi Logistik'),
        ('normality', 'Uji Normalitas'),
        ('chi_square', 'Chi-Square'),
        ('mann_whitney', 'Mann-Whitney U'),
        ('wilcoxon', 'Wilcoxon'),
        ('kruskal_wallis', 'Kruskal-Wallis'),
        ('factor', 'Analisis Faktor'),
        ('cluster', 'Analisis Klaster'),
        ('reliability', 'Reliabilitas (Alpha)'),
    ]

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='analyses')
    analysis_type = models.CharField(max_length=50, choices=ANALYSIS_TYPES)
    parameters = models.TextField(default='{}')  # JSON: input parameters
    output_html = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.analysis_type} - {self.dataset.name}"

    def get_parameters(self):
        return json.loads(self.parameters)


class ChartResult(models.Model):
    CHART_TYPES = [
        ('bar', 'Bar Chart'),
        ('histogram', 'Histogram'),
        ('scatter', 'Scatter Plot'),
        ('box', 'Box Plot'),
        ('line', 'Line Chart'),
        ('pie', 'Pie Chart'),
    ]

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='charts')
    chart_type = models.CharField(max_length=30, choices=CHART_TYPES)
    parameters = models.TextField(default='{}')
    chart_json = models.TextField(default='{}')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
