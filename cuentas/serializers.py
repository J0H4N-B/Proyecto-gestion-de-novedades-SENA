from django.contrib.auth.password_validation import validate_password
from django.urls import reverse
from rest_framework import serializers

from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})
    foto_url = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            "id", "username", "first_name", "last_name", "email", "tipo_doc", "numero_documento",
            "telefono", "rol", "sede", "ficha", "is_active", "foto", "foto_url", "password",
        ]
        extra_kwargs = {"foto": {"write_only": True}}

    def get_foto_url(self, usuario):
        if not usuario.foto:
            return None
        return self.context["request"].build_absolute_uri(reverse("cuentas:foto", args=[usuario.pk]))

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if self.instance is None and "password" not in attrs:
            raise serializers.ValidationError({"password": "Este campo es obligatorio."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return Usuario.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        usuario = super().update(instance, validated_data)
        if password:
            usuario.set_password(password)
            usuario.save(update_fields=["password"])
        return usuario
