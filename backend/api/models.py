from django.db import models #create db tables in Django
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
# Create your models here.
"""
Class definitions
tell Django how to create db tables and what fields/methods each model has

This file contains all database models for tracking user performance,
learning progress, and API metrics.
"""
class UserPerformanceMetric(models.Model):
    """
    Tracks performance metrics for individual users.
    Used to demonstrate database optimization through indexing.
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='performance_metrics'
    )
    metric_type = models.CharField(
        max_length=50,
        choices=[
            ('page_load', 'Page Load Time'),
            ('api_response', 'API Response Time'),
            ('engagement', 'User Engagement Score'),
            ('conversion', 'Conversion Rate'),
        ],
        db_index=True  # Index for faster filtering
    )
    value = models.FloatField(
        validators=[MinValueValidator(0.0)],
        help_text="Metric value (milliseconds for time, percentage for rates)"
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True  # Index for time-based queries
    )
    is_optimized = models.BooleanField(
        default=False,
        help_text="Whether this metric was recorded after optimizations"
    )
    
    class Meta:
        ordering = ['-timestamp']
        # Composite index for common query patterns
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['metric_type', 'is_optimized']),
            models.Index(fields=['timestamp', 'metric_type']),
        ]
        verbose_name = "User Performance Metric"
        verbose_name_plural = "User Performance Metrics"
    
    def __str__(self):
        return f"{self.user.username} - {self.metric_type}: {self.value} at {self.timestamp}"
    
    @property
    def improvement_percentage(self):
        """Calculate improvement if this is an optimized metric"""
        if not self.is_optimized:
            return None
        
        # Get baseline (pre-optimization) metric
        baseline = UserPerformanceMetric.objects.filter(
            user=self.user,
            metric_type=self.metric_type,
            is_optimized=False,
            timestamp__lt=self.timestamp
        ).order_by('-timestamp').first()
        
        if baseline:
            improvement = ((baseline.value - self.value) / baseline.value) * 100
            return round(improvement, 2)
        return None


class Course(models.Model):
    """
    Represents courses available on the CoderPush platform.
    """
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField()
    difficulty = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
        ],
        default='beginner'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)
    total_lessons = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['title']
        indexes = [
            models.Index(fields=['difficulty', 'is_active']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def enrollment_count(self):
        """Get total number of enrolled users"""
        return self.learning_progress.values('user').distinct().count()


class LearningProgress(models.Model):
    """
    Tracks individual user progress through courses.
    Demonstrates select_related and prefetch_related optimization.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='learning_progress'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='learning_progress'
    )
    lessons_completed = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    current_lesson = models.PositiveIntegerField(default=1)
    completion_percentage = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    started_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Total time spent on this course in minutes"
    )
    
    class Meta:
        ordering = ['-last_accessed']
        unique_together = ['user', 'course']  # Each user can only enroll once per course
        indexes = [
            models.Index(fields=['user', 'course']),
            models.Index(fields=['user', 'last_accessed']),
            models.Index(fields=['completion_percentage']),
        ]
        verbose_name = "Learning Progress"
        verbose_name_plural = "Learning Progress Records"
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title} ({self.completion_percentage}%)"
    
    def save(self, *args, **kwargs):
        """Auto-calculate completion percentage before saving"""
        if self.course.total_lessons > 0:
            self.completion_percentage = (
                self.lessons_completed / self.course.total_lessons
            ) * 100
        
        # Mark as completed if 100%
        if self.completion_percentage >= 100 and not self.completed_at:
            self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def is_completed(self):
        """Check if course is completed"""
        return self.completion_percentage >= 100
    
    @property
    def days_since_start(self):
        """Calculate days since course started"""
        return (timezone.now() - self.started_at).days


class APIResponseLog(models.Model):
    """
    Logs API response times to track performance improvements.
    Used to demonstrate the impact of caching and optimization.
    """
    endpoint = models.CharField(
        max_length=200,
        db_index=True,
        help_text="API endpoint path (e.g., /api/courses/)"
    )
    method = models.CharField(
        max_length=10,
        choices=[
            ('GET', 'GET'),
            ('POST', 'POST'),
            ('PUT', 'PUT'),
            ('PATCH', 'PATCH'),
            ('DELETE', 'DELETE'),
        ],
        db_index=True
    )
    response_time_ms = models.FloatField(
        validators=[MinValueValidator(0.0)],
        help_text="Response time in milliseconds"
    )
    status_code = models.PositiveIntegerField(db_index=True)
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='api_logs'
    )
    cache_hit = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this request was served from cache"
    )
    query_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of database queries executed"
    )
    request_size_bytes = models.PositiveIntegerField(
        default=0,
        help_text="Size of request payload in bytes"
    )
    response_size_bytes = models.PositiveIntegerField(
        default=0,
        help_text="Size of response payload in bytes"
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['endpoint', 'timestamp']),
            models.Index(fields=['cache_hit', 'timestamp']),
            models.Index(fields=['method', 'status_code']),
            models.Index(fields=['timestamp', 'response_time_ms']),
        ]
        verbose_name = "API Response Log"
        verbose_name_plural = "API Response Logs"
    
    def __str__(self):
        cache_status = "CACHED" if self.cache_hit else "DB"
        return f"{self.method} {self.endpoint} - {self.response_time_ms}ms [{cache_status}]"
    
    @classmethod
    def get_average_response_time(cls, endpoint=None, hours=24):
        """Calculate average response time for an endpoint"""
        from django.db.models import Avg
        from datetime import timedelta
        
        since = timezone.now() - timedelta(hours=hours)
        queryset = cls.objects.filter(timestamp__gte=since)
        
        if endpoint:
            queryset = queryset.filter(endpoint=endpoint)
        
        result = queryset.aggregate(avg_time=Avg('response_time_ms'))
        return result['avg_time'] or 0
    
    @classmethod
    def get_cache_hit_rate(cls, hours=24):
        """Calculate cache hit rate percentage"""
        from datetime import timedelta
        
        since = timezone.now() - timedelta(hours=hours)
        total = cls.objects.filter(timestamp__gte=since).count()
        
        if total == 0:
            return 0
        
        cached = cls.objects.filter(
            timestamp__gte=since,
            cache_hit=True
        ).count()
        
        return (cached / total) * 100


class SystemMetric(models.Model):
    """
    Tracks overall system performance metrics.
    Used for dashboard and monitoring.
    """
    metric_name = models.CharField(
        max_length=100,
        db_index=True,
        choices=[
            ('total_users', 'Total Users'),
            ('active_users', 'Active Users (24h)'),
            ('avg_page_load', 'Average Page Load Time'),
            ('avg_api_response', 'Average API Response Time'),
            ('db_query_avg', 'Average DB Query Time'),
            ('cache_hit_rate', 'Cache Hit Rate'),
            ('error_rate', 'Error Rate'),
            ('concurrent_users', 'Concurrent Users'),
        ]
    )
    value = models.FloatField()
    unit = models.CharField(
        max_length=20,
        default='count',
        help_text="Unit of measurement (ms, %, count, etc.)"
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['metric_name', 'timestamp']),
        ]
        verbose_name = "System Metric"
        verbose_name_plural = "System Metrics"
    
    def __str__(self):
        return f"{self.metric_name}: {self.value} {self.unit} at {self.timestamp}"
    
    @classmethod
    def record_metric(cls, metric_name, value, unit='count'):
        """Helper method to record a new metric"""
        return cls.objects.create(
            metric_name=metric_name,
            value=value,
            unit=unit
        )