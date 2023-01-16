# coding: utf-8

from rest_framework import serializers
from .models import *

# 
class AmazonParentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AmazonParentCategory
        fields = ('name', 'value')

# 
class AmazonParentCategoryUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmazonParentCategoryUser
        fields = ('name', 'value')


# メーカ名
class AmazonBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmazonBrand
        fields = ('brand_name', )


        
# Amazonカテゴリー（ホビー）
class AmazonHobbiesCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AmazonHobbiesCategory
        fields = ('name', 'value')

# Amazonカテゴリー（ホビー:ユーザ）
class AmazonHobbiesCategoryUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmazonHobbiesCategoryUser
        fields = ('name', 'value')


# Amazonカテゴリー（ペット用品）
class AmazonPetSuppliesCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AmazonPetSuppliesCategory
        fields = ('name', 'value')

# Amazonカテゴリー（ホビー:ペット用品）
class AmazonPetSuppliesCategoryUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmazonPetSuppliesCategoryUser
        fields = ('name', 'value')



        




