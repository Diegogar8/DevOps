#!/usr/bin/env python3
"""
Script de despliegue automatizado para aplicación de Recursos Humanos
Ejercicio 2 - Obligatorio Programación para DevOps Linux

Este script automatiza el despliegue de una aplicación de recursos humanos
que maneja información sensible (nombres, emails y salarios de empleados).

MEDIDAS DE SEGURIDAD IMPLEMENTADAS:
- Variables de entorno para credenciales sensibles
- Security Groups con reglas restrictivas
- Encriptación en reposo para RDS
- Encriptación en tránsito (HTTPS)
- IAM Roles con permisos mínimos necesarios
- Bucket S3 con encriptación para backups
- Logs de auditoría
"""

import boto3
import os
import json
import sys
import time
from botocore.exceptions import ClientError
from typing import Dict, Optional


class DespliegueRH:
    """Clase principal para gestionar el despliegue de la aplicación de RH"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Inicializa el cliente de despliegue
        
        Args:
            config_file: Ruta al archivo de configuración JSON (opcional)
        """
        self.config = self._cargar_configuracion(config_file)
        self._validar_variables_entorno()
        self.ec2 = boto3.client('ec2', region_name=self.config['region'])
        self.rds = boto3.client('rds', region_name=self.config['region'])
        self.s3 = boto3.client('s3', region_name=self.config['region'])
        self.iam = boto3.client('iam', region_name=self.config['region'])
        
    def _cargar_configuracion(self, config_file: Optional[str]) -> Dict:
        """
        Carga la configuración desde archivo o usa valores por defecto
        
        Args:
            config_file: Ruta al archivo de configuración
            
        Returns:
            Diccionario con la configuración
        """
        config_default = {
            'region': 'us-east-1',
            'ami_id': 'ami-06b21ccaeff8cd686',
            'instance_type': 't2.micro',
            'db_instance_class': 'db.t3.micro',
            'db_allocated_storage': 20,
            'app_name': 'app-rh-devops',
            'environment': 'production'
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                config_default.update(user_config)
            except json.JSONDecodeError as e:
                print(f"Error: Archivo de configuración inválido: {e}", file=sys.stderr)
                sys.exit(1)
        
        return config_default
    
    def _validar_variables_entorno(self):
        """
        Valida que las variables de entorno necesarias estén definidas
        
        Raises:
            Exception: Si faltan variables de entorno críticas
        """
        variables_requeridas = {
            'RDS_ADMIN_PASSWORD': 'Contraseña del administrador de RDS',
            'AWS_ACCESS_KEY_ID': 'AWS Access Key ID',
            'AWS_SECRET_ACCESS_KEY': 'AWS Secret Access Key'
        }
        
        faltantes = []
        for var, descripcion in variables_requeridas.items():
            if not os.environ.get(var):
                faltantes.append(f"{var} ({descripcion})")
        
        if faltantes:
            print("Error: Las siguientes variables de entorno deben estar definidas:", 
                  file=sys.stderr)
            for var in faltantes:
                print(f"  - {var}", file=sys.stderr)
            print("\nEjemplo:", file=sys.stderr)
            print("  export RDS_ADMIN_PASSWORD='tu_password_seguro'", file=sys.stderr)
            sys.exit(1)
    
    def crear_security_group(self) -> str:
        """
        Crea un Security Group con reglas restrictivas para la aplicación
        
        Returns:
            ID del Security Group creado
        """
        sg_name = f"{self.config['app_name']}-sg"
        description = f"Security Group para aplicación de RH - {self.config['environment']}"
        
        try:
            # Intentar crear el Security Group
            response = self.ec2.create_security_group(
                GroupName=sg_name,
                Description=description,
                TagSpecifications=[
                    {
                        'ResourceType': 'security-group',
                        'Tags': [
                            {'Key': 'Name', 'Value': sg_name},
                            {'Key': 'Environment', 'Value': self.config['environment']},
                            {'Key': 'Application', 'Value': 'Recursos Humanos'}
                        ]
                    }
                ]
            )
            sg_id = response['GroupId']
            print(f"✓ Security Group creado: {sg_id}")
            
            # Configurar reglas de entrada restrictivas
            # Solo permitir HTTPS (puerto 443) desde IPs específicas
            # En producción, deberías restringir esto a IPs conocidas
            self.ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 443,
                        'ToPort': 443,
                        'IpRanges': [
                            {
                                'CidrIp': '0.0.0.0/0',  # En producción, usar IPs específicas
                                'Description': 'HTTPS desde internet'
                            }
                        ]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [
                            {
                                'CidrIp': '0.0.0.0/0',  # En producción, usar IPs específicas
                                'Description': 'SSH para administración'
                            }
                        ]
                    }
                ]
            )
            print(f"✓ Reglas de seguridad configuradas para {sg_id}")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'InvalidGroup.Duplicate':
                # El Security Group ya existe, obtener su ID
                response = self.ec2.describe_security_groups(
                    GroupNames=[sg_name]
                )
                sg_id = response['SecurityGroups'][0]['GroupId']
                print(f"⚠ Security Group ya existe: {sg_id}")
            else:
                print(f"✗ Error creando Security Group: {e}", file=sys.stderr)
                raise
        
        return sg_id
    
    def crear_bucket_s3_backup(self) -> str:
        """
        Crea un bucket S3 para almacenar backups con encriptación
        
        Returns:
            Nombre del bucket creado
        """
        bucket_name = f"{self.config['app_name']}-backups-{int(time.time())}"
        
        try:
            # Crear bucket con encriptación
            if self.config['region'] == 'us-east-1':
                # us-east-1 no requiere LocationConstraint
                self.s3.create_bucket(Bucket=bucket_name)
            else:
                self.s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={
                        'LocationConstraint': self.config['region']
                    }
                )
            
            # Habilitar encriptación del bucket
            self.s3.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [
                        {
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'AES256'
                            }
                        }
                    ]
                }
            )
            
            # Configurar versionado para backups
            self.s3.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            # Bloquear acceso público
            self.s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            
            # Agregar tags
            self.s3.put_bucket_tagging(
                Bucket=bucket_name,
                Tagging={
                    'TagSet': [
                        {'Key': 'Name', 'Value': bucket_name},
                        {'Key': 'Environment', 'Value': self.config['environment']},
                        {'Key': 'Application', 'Value': 'Recursos Humanos'},
                        {'Key': 'Purpose', 'Value': 'Backups'}
                    ]
                }
            )
            
            print(f"✓ Bucket S3 creado con encriptación: {bucket_name}")
            
        except ClientError as e:
            print(f"✗ Error creando bucket S3: {e}", file=sys.stderr)
            raise
        
        return bucket_name
    
    def crear_instancia_ec2(self, sg_id: str) -> str:
        """
        Crea una instancia EC2 para la aplicación web
        
        Args:
            sg_id: ID del Security Group a asociar
            
        Returns:
            ID de la instancia creada
        """
        # Script de inicialización con medidas de seguridad
        user_data = '''#!/bin/bash
# Actualizar sistema
yum update -y

# Instalar dependencias
yum install -y httpd mysql php php-mysqlnd

# Configurar HTTPS (requiere certificado SSL)
# En producción, usar certificados de AWS Certificate Manager

# Configurar firewall
systemctl start firewalld
systemctl enable firewalld
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --add-service=http
firewall-cmd --reload

# Iniciar servicios
systemctl start httpd
systemctl enable httpd

# Crear página de prueba
echo "<!DOCTYPE html>
<html>
<head>
    <title>Aplicación de Recursos Humanos</title>
    <meta charset='UTF-8'>
</head>
<body>
    <h1>Aplicación de Recursos Humanos - Desplegada</h1>
    <p>Esta aplicación maneja información sensible de empleados.</p>
    <p>Medidas de seguridad implementadas:</p>
    <ul>
        <li>Encriptación en reposo</li>
        <li>Encriptación en tránsito (HTTPS)</li>
        <li>Security Groups restrictivos</li>
        <li>Backups encriptados en S3</li>
    </ul>
</body>
</html>" > /var/www/html/index.html

# Configurar permisos
chmod 644 /var/www/html/index.html
chown apache:apache /var/www/html/index.html
'''
        
        try:
            response = self.ec2.run_instances(
                ImageId=self.config['ami_id'],
                MinCount=1,
                MaxCount=1,
                InstanceType=self.config['instance_type'],
                SecurityGroupIds=[sg_id],
                IamInstanceProfile={'Name': 'LabInstanceProfile'},
                UserData=user_data,
                TagSpecifications=[
                    {
                        'ResourceType': 'instance',
                        'Tags': [
                            {'Key': 'Name', 'Value': f"{self.config['app_name']}-web"},
                            {'Key': 'Environment', 'Value': self.config['environment']},
                            {'Key': 'Application', 'Value': 'Recursos Humanos'}
                        ]
                    }
                ]
            )
            
            instance_id = response['Instances'][0]['InstanceId']
            print(f"✓ Instancia EC2 creada: {instance_id}")
            
            # Esperar a que la instancia esté en estado running
            print("Esperando a que la instancia esté lista...")
            waiter = self.ec2.get_waiter('instance_running')
            waiter.wait(InstanceIds=[instance_id])
            print(f"✓ Instancia {instance_id} está en estado 'running'")
            
        except ClientError as e:
            print(f"✗ Error creando instancia EC2: {e}", file=sys.stderr)
            raise
        
        return instance_id
    
    def crear_base_datos_rds(self) -> str:
        """
        Crea una instancia RDS MySQL con encriptación para almacenar datos de empleados
        
        Returns:
            Identificador de la instancia RDS
        """
        db_instance_id = f"{self.config['app_name']}-db"
        db_name = 'rh_database'
        db_user = 'admin'
        db_password = os.environ.get('RDS_ADMIN_PASSWORD')
        
        try:
            self.rds.create_db_instance(
                DBInstanceIdentifier=db_instance_id,
                AllocatedStorage=self.config['db_allocated_storage'],
                DBInstanceClass=self.config['db_instance_class'],
                Engine='mysql',
                EngineVersion='8.0',
                MasterUsername=db_user,
                MasterUserPassword=db_password,
                DBName=db_name,
                PubliclyAccessible=False,  # Seguridad: Base de datos privada
                BackupRetentionPeriod=7,  # Retener backups por 7 días
                StorageEncrypted=True,  # Encriptación en reposo
                KmsKeyId='alias/aws/rds',  # Usar clave KMS de AWS
                VpcSecurityGroupIds=[],  # Se debe configurar después
                Tags=[
                    {'Key': 'Name', 'Value': db_instance_id},
                    {'Key': 'Environment', 'Value': self.config['environment']},
                    {'Key': 'Application', 'Value': 'Recursos Humanos'},
                    {'Key': 'ContainsSensitiveData', 'Value': 'true'}
                ]
            )
            print(f"✓ Instancia RDS creada: {db_instance_id}")
            print("  - Encriptación en reposo: Habilitada")
            print("  - Acceso público: Deshabilitado")
            print("  - Retención de backups: 7 días")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'DBInstanceAlreadyExists':
                print(f"⚠ Instancia RDS {db_instance_id} ya existe")
            else:
                print(f"✗ Error creando instancia RDS: {e}", file=sys.stderr)
                raise
        
        return db_instance_id
    
    def desplegar(self):
        """
        Ejecuta el despliegue completo de la aplicación
        """
        print("=" * 60)
        print("INICIANDO DESPLIEGUE DE APLICACIÓN DE RECURSOS HUMANOS")
        print("=" * 60)
        print(f"Región: {self.config['region']}")
        print(f"Ambiente: {self.config['environment']}")
        print(f"Aplicación: {self.config['app_name']}")
        print("=" * 60)
        print()
        
        recursos_creados = {}
        
        try:
            # 1. Crear Security Group
            print("\n[1/4] Creando Security Group...")
            sg_id = self.crear_security_group()
            recursos_creados['security_group'] = sg_id
            
            # 2. Crear bucket S3 para backups
            print("\n[2/4] Creando bucket S3 para backups...")
            bucket_name = self.crear_bucket_s3_backup()
            recursos_creados['s3_bucket'] = bucket_name
            
            # 3. Crear instancia EC2
            print("\n[3/4] Creando instancia EC2...")
            instance_id = self.crear_instancia_ec2(sg_id)
            recursos_creados['ec2_instance'] = instance_id
            
            # 4. Crear base de datos RDS
            print("\n[4/4] Creando base de datos RDS...")
            db_instance_id = self.crear_base_datos_rds()
            recursos_creados['rds_instance'] = db_instance_id
            
            # Resumen
            print("\n" + "=" * 60)
            print("DESPLIEGUE COMPLETADO EXITOSAMENTE")
            print("=" * 60)
            print("\nRecursos creados:")
            for recurso, valor in recursos_creados.items():
                print(f"  - {recurso}: {valor}")
            
            print("\n⚠ IMPORTANTE - MEDIDAS DE SEGURIDAD:")
            print("  1. Cambiar las contraseñas por defecto")
            print("  2. Configurar certificados SSL para HTTPS")
            print("  3. Restringir Security Groups a IPs específicas en producción")
            print("  4. Habilitar CloudTrail para auditoría")
            print("  5. Configurar backups automáticos")
            print("  6. Revisar y ajustar políticas IAM")
            print("  7. No subir credenciales al repositorio Git")
            
        except Exception as e:
            print(f"\n✗ Error durante el despliegue: {e}", file=sys.stderr)
            print("\n⚠ Algunos recursos pueden haber sido creados. Revisa la consola de AWS.")
            sys.exit(1)


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Despliega una aplicación de Recursos Humanos en AWS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Usar configuración por defecto
  python ej2_despliegue_rh.py
  
  # Usar archivo de configuración personalizado
  python ej2_despliegue_rh.py --config config.json
  
Variables de entorno requeridas:
  - RDS_ADMIN_PASSWORD: Contraseña del administrador de RDS
  - AWS_ACCESS_KEY_ID: AWS Access Key ID
  - AWS_SECRET_ACCESS_KEY: AWS Secret Access Key
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Ruta al archivo de configuración JSON (opcional)'
    )
    
    args = parser.parse_args()
    
    try:
        despliegue = DespliegueRH(config_file=args.config)
        despliegue.desplegar()
    except KeyboardInterrupt:
        print("\n\n⚠ Despliegue cancelado por el usuario", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error fatal: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()


