from rest_framework import serializers
from .models import BOM, BOMLine, ProductionOrder, MRPPlan


class BOMLineSerializer(serializers.ModelSerializer):
    component_material_name = serializers.CharField(
        source='component_material.material_name', read_only=True
    )
    component_material_code = serializers.CharField(
        source='component_material.material_code', read_only=True
    )

    class Meta:
        model  = BOMLine
        fields = '__all__'


class BOMSerializer(serializers.ModelSerializer):
    lines         = BOMLineSerializer(many=True, read_only=True)
    material_name = serializers.CharField(source='material.material_name', read_only=True)
    material_code = serializers.CharField(source='material.material_code', read_only=True)
    # Frontend compatibility aliases
    bom_code      = serializers.CharField(source='material.material_code', read_only=True, default='')
    product_name  = serializers.CharField(source='material.material_name', read_only=True, default='')
    bom_lines     = BOMLineSerializer(source='lines', many=True, read_only=True)

    class Meta:
        model  = BOM
        fields = '__all__'


class BOMLineWriteSerializer(serializers.Serializer):
    """BOM 라인 write 전용 - material FK 불필요, 코드/이름만 받음"""
    material_code = serializers.CharField(required=False, allow_blank=True)
    material_name = serializers.CharField(required=False, allow_blank=True)
    quantity      = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, allow_null=True)
    unit          = serializers.CharField(required=False, allow_blank=True, default='EA')
    component_material = serializers.PrimaryKeyRelatedField(
        queryset=__import__('scm_mm.models', fromlist=['Material']).Material.objects.all(),
        required=False, allow_null=True
    )


class BOMWriteSerializer(serializers.ModelSerializer):
    """생성/수정 전용 - lines 포함 nested write 지원"""
    lines = BOMLineWriteSerializer(many=True, required=False)
    # Accept legacy fields from frontend (ignored during save)
    bom_code     = serializers.CharField(write_only=True, required=False, allow_blank=True)
    product_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model  = BOM
        fields = '__all__'
        extra_kwargs = {
            'material': {'required': False, 'allow_null': True},
        }

    def create(self, validated_data):
        validated_data.pop('bom_code', None)
        validated_data.pop('product_name', None)
        lines_data = validated_data.pop('lines', [])
        bom = BOM.objects.create(**validated_data)
        for line_data in lines_data:
            line_data.pop('material_code', None)
            line_data.pop('material_name', None)
            component = line_data.pop('component_material', None)
            qty = line_data.pop('quantity', None)
            unit = line_data.pop('unit', 'EA')
            if component and qty is not None:
                BOMLine.objects.create(
                    bom=bom, component_material=component,
                    quantity=qty, unit=unit
                )
        return bom

    def update(self, instance, validated_data):
        validated_data.pop('bom_code', None)
        validated_data.pop('product_name', None)
        lines_data = validated_data.pop('lines', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            for line_data in lines_data:
                line_data.pop('material_code', None)
                line_data.pop('material_name', None)
                component = line_data.pop('component_material', None)
                qty = line_data.pop('quantity', None)
                unit = line_data.pop('unit', 'EA')
                if component and qty is not None:
                    BOMLine.objects.create(
                        bom=instance, component_material=component,
                        quantity=qty, unit=unit
                    )
        return instance


class ProductionOrderSerializer(serializers.ModelSerializer):
    status_display    = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name   = serializers.CharField(source='created_by.name', read_only=True)
    bom_material_name = serializers.CharField(source='bom.material.material_name', read_only=True)
    bom_material_code = serializers.CharField(source='bom.material.material_code', read_only=True)
    # Accept legacy fields from frontend (ignored during save)
    product_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    work_center  = serializers.CharField(write_only=True, required=False, allow_blank=True)
    note         = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def create(self, validated_data):
        for f in ('product_name', 'work_center', 'note'):
            validated_data.pop(f, None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        for f in ('product_name', 'work_center', 'note'):
            validated_data.pop(f, None)
        return super().update(instance, validated_data)

    class Meta:
        model  = ProductionOrder
        fields = '__all__'
        extra_kwargs = {
            'bom': {'required': False, 'allow_null': True},
        }


class MRPPlanSerializer(serializers.ModelSerializer):
    status_display   = serializers.CharField(source='get_status_display', read_only=True)
    material_name    = serializers.CharField(source='material.material_name', read_only=True)
    material_code    = serializers.CharField(source='material.material_code', read_only=True)
    material_unit    = serializers.CharField(source='material.unit', read_only=True)

    class Meta:
        model  = MRPPlan
        fields = '__all__'
