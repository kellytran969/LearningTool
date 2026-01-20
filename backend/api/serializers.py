"""
API Serializers
Bridge between Django models and JSON API
Converts Django models to/from JSON for the REST API.
Includes validation and nested serialization.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    UserPerformanceMetric,
    Course,
    LearningProgress,
    APIResponseLog,
    SystemMetric
)
from django.db.models import Avg, Count
from datetime import timedelta
from django.utils import timezone


class UserSerializer(serializers.ModelSerializer):
    """
    convert User model to JSON (define how data is converted)
    Serializer for User model.
    Includes computed fields for user statistics.
    """
    total_courses = serializers.SerializerMethodField() #number of course user enrolled in
    completed_courses = serializers.SerializerMethodField() #course finish
    average_completion = serializers.SerializerMethodField() #average progress %
    total_time_spent = serializers.SerializerMethodField() # mins spent across all course
    
    class Meta: #tells Django REST Framework how to configure serializer
        model = User #tell serializer which Django model it's based on
        fields = [ #list all fields i want to include in the serialized JSON
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'date_joined',
            'total_courses',
            'completed_courses',
            'average_completion',
            'total_time_spent'
        ]
        read_only_fields = ['id', 'date_joined'] #cannot be changed by client
    
    #call methods to get value
    def get_total_courses(self, obj):
        """Get total number of courses user is enrolled in"""
        return obj.learning_progress.count()
    
    def get_completed_courses(self, obj):
        """Get number of completed courses"""
        return obj.learning_progress.filter(completion_percentage=100).count()
    
    def get_average_completion(self, obj):
        """Calculate average completion percentage across all courses"""
        avg = obj.learning_progress.aggregate(
            avg_completion=Avg('completion_percentage')
        )
        return round(avg['avg_completion'] or 0, 2)
    
    def get_total_time_spent(self, obj):
        """Get total time spent learning (in minutes)"""
        total = obj.learning_progress.aggregate(
            total_time=models.Sum('time_spent_minutes')
        )
        return total['total_time'] or 0


class CourseSerializer(serializers.ModelSerializer):
    """
    Serializer for Course model.
    Includes enrollment statistics.
    """
    enrollment_count = serializers.ReadOnlyField() #total students
    average_progress = serializers.SerializerMethodField() #average completion %
    completion_rate = serializers.SerializerMethodField() #% of students who finished
    
    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'description',
            'difficulty',
            'total_lessons',
            'created_at',
            'updated_at',
            'is_active',
            'enrollment_count',
            'average_progress',
            'completion_rate'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_average_progress(self, obj):
        """Calculate average completion percentage for this course"""
        avg = obj.learning_progress.aggregate(
            avg_progress=Avg('completion_percentage')
        )
        return round(avg['avg_progress'] or 0, 2)
    
    def get_completion_rate(self, obj):
        """Calculate percentage of enrolled users who completed the course"""
        total_enrolled = obj.learning_progress.count()
        if total_enrolled == 0:
            return 0
        
        completed = obj.learning_progress.filter(completion_percentage=100).count()
        return round((completed / total_enrolled) * 100, 2)


class LearningProgressSerializer(serializers.ModelSerializer):
    """
    Serializer for LearningProgress model.
    Includes user and course details with optimization.
    """
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_difficulty = serializers.CharField(source='course.difficulty', read_only=True)
    is_completed = serializers.ReadOnlyField()
    days_since_start = serializers.ReadOnlyField()
    
    class Meta:
        model = LearningProgress
        fields = [
            'id',
            'user',
            'user_username',
            'user_email',
            'course',
            'course_title',
            'course_difficulty',
            'lessons_completed',
            'current_lesson',
            'completion_percentage',
            'started_at',
            'last_accessed',
            'completed_at',
            'time_spent_minutes',
            'is_completed',
            'days_since_start'
        ]
        read_only_fields = [
            'id',
            'started_at',
            'completion_percentage',
            'completed_at'
        ]
    
    def validate_lessons_completed(self, value):
        """validate lessons_completed doesn't exceed total_lessons"""
        if self.instance:
            course = self.instance.course
        elif 'course' in self.initial_data:
            course = Course.objects.get(id=self.initial_data['course'])
        else:
            return value
        
        if value > course.total_lessons:
            raise serializers.ValidationError(
                f"Cannot complete more than {course.total_lessons} lessons"
            )
        return value


class LearningProgressDetailSerializer(LearningProgressSerializer):
    """
    Detailed serializer with full user and course objects instead just
    Use this when you need complete nested data.
    """
    user = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    
    class Meta(LearningProgressSerializer.Meta):
        fields = LearningProgressSerializer.Meta.fields


class UserPerformanceMetricSerializer(serializers.ModelSerializer):
    #how effectively, efficiently, satisfactorily users interact with product
    """
    Serializer for UserPerformanceMetric model.
    Includes improvement calculations.
    """
    user_username = serializers.CharField(source='user.username', read_only=True)
    improvement_percentage = serializers.ReadOnlyField()
    metric_type_display = serializers.CharField(
        source='get_metric_type_display',
        read_only=True
    )
    
    class Meta:
        model = UserPerformanceMetric
        fields = [
            'id',
            'user',
            'user_username',
            'metric_type',
            'metric_type_display',
            'value',
            'timestamp',
            'is_optimized',
            'improvement_percentage'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def validate_value(self, value):
        """Ensure metric value is positive"""
        if value < 0:
            raise serializers.ValidationError("Metric value must be positive")
        return value


class PerformanceComparisonSerializer(serializers.Serializer):
    """
    Custom serializer for comparing performance before/after optimization.
    Not tied to a specific model.
    """
    metric_type = serializers.CharField()
    before_optimization = serializers.FloatField()
    after_optimization = serializers.FloatField()
    improvement_percentage = serializers.FloatField()
    sample_size = serializers.IntegerField()
    
    class Meta:
        fields = [
            'metric_type',
            'before_optimization',
            'after_optimization',
            'improvement_percentage',
            'sample_size'
        ]


class APIResponseLogSerializer(serializers.ModelSerializer):
    """
    Serializer for APIResponseLog model.
    Tracks API performance metrics.
    """
    user_username = serializers.CharField(
        source='user.username',
        read_only=True,
        allow_null=True
    )
    method_display = serializers.CharField(
        source='get_method_display',
        read_only=True
    )
    
    class Meta:
        model = APIResponseLog
        fields = [
            'id',
            'endpoint',
            'method',
            'method_display',
            'response_time_ms',
            'status_code',
            'timestamp',
            'user',
            'user_username',
            'cache_hit',
            'query_count',
            'request_size_bytes',
            'response_size_bytes'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def validate_status_code(self, value):
        """Validate HTTP status code"""
        if value < 100 or value > 599:
            raise serializers.ValidationError("Invalid HTTP status code")
        return value


class APIPerformanceStatsSerializer(serializers.Serializer):
    """
    Custom serializer for API performance statistics.
    Used in dashboard endpoints.
    """
    endpoint = serializers.CharField()
    total_requests = serializers.IntegerField()
    average_response_time = serializers.FloatField()
    min_response_time = serializers.FloatField()
    max_response_time = serializers.FloatField()
    cache_hit_rate = serializers.FloatField()
    error_rate = serializers.FloatField()
    p95_response_time = serializers.FloatField(required=False)
    
    class Meta:
        fields = [
            'endpoint',
            'total_requests',
            'average_response_time',
            'min_response_time',
            'max_response_time',
            'cache_hit_rate',
            'error_rate',
            'p95_response_time'
        ]


class SystemMetricSerializer(serializers.ModelSerializer):
    """
    Serializer for SystemMetric model.
    System-wide performance tracking.
    """
    metric_name_display = serializers.CharField(
        source='get_metric_name_display',
        read_only=True
    )
    
    class Meta:
        model = SystemMetric
        fields = [
            'id',
            'metric_name',
            'metric_name_display',
            'value',
            'unit',
            'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class DashboardSerializer(serializers.Serializer):
    """
    Custom serializer for main dashboard endpoint.
    Aggregates multiple metrics.
    """
    total_users = serializers.IntegerField()
    active_users_24h = serializers.IntegerField()
    total_courses = serializers.IntegerField()
    total_enrollments = serializers.IntegerField()
    average_completion_rate = serializers.FloatField()
    
    # Performance metrics
    avg_page_load_time = serializers.FloatField()
    avg_api_response_time = serializers.FloatField()
    cache_hit_rate = serializers.FloatField()
    
    # Improvement metrics
    performance_improvement = serializers.FloatField()
    engagement_improvement = serializers.FloatField()
    
    class Meta:
        fields = [
            'total_users',
            'active_users_24h',
            'total_courses',
            'total_enrollments',
            'average_completion_rate',
            'avg_page_load_time',
            'avg_api_response_time',
            'cache_hit_rate',
            'performance_improvement',
            'engagement_improvement'
        ]


class OptimizationImpactSerializer(serializers.Serializer):
    """
    Serializer showing the impact of optimizations.
    Perfect for portfolio demonstration.
    """
    category = serializers.CharField()
    before_value = serializers.FloatField()
    after_value = serializers.FloatField()
    improvement_percentage = serializers.FloatField()
    unit = serializers.CharField()
    description = serializers.CharField()
    
    class Meta:
        fields = [
            'category',
            'before_value',
            'after_value',
            'improvement_percentage',
            'unit',
            'description'
        ]


class BulkLearningProgressSerializer(serializers.Serializer):
    """
    Serializer for bulk updating learning progress.
    Demonstrates efficient batch operations.
    """
    user_id = serializers.IntegerField()
    course_id = serializers.IntegerField()
    lessons_completed = serializers.IntegerField(min_value=0)
    time_spent_minutes = serializers.IntegerField(min_value=0)
    
    def validate(self, data):
        """Validate that user and course exist"""
        try:
            User.objects.get(id=data['user_id'])
        except User.DoesNotExist:
            raise serializers.ValidationError(
                f"User with id {data['user_id']} does not exist"
            )
        
        try:
            Course.objects.get(id=data['course_id'])
        except Course.DoesNotExist:
            raise serializers.ValidationError(
                f"Course with id {data['course_id']} does not exist"
            )
        
        return data
    
    class Meta:
        fields = [
            'user_id',
            'course_id',
            'lessons_completed',
            'time_spent_minutes'
        ]


# Import statement needed for Sum aggregation
from django.db import models