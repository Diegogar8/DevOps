# Script de Creación de Usuarios - Banco Riendo

Este script permite crear múltiples usuarios en Linux desde un archivo de configuración.

## Requisitos

- Sistema operativo Linux
- Permisos de root (sudo)
- Bash shell

## Uso

```bash
sudo ./crear_usuarios.sh -f archivo_usuarios.txt [-p PASSWORD] [-v]
```

### Opciones

- `-f ARCHIVO`: Archivo con la información de usuarios (obligatorio)
- `-p PASSWORD`: Contraseña para todos los usuarios (opcional)
- `-v`: Modo verbose - muestra información detallada
- `-h`: Muestra la ayuda

## Formato del Archivo de Usuarios

El archivo debe contener un usuario por línea con el siguiente formato:

```
usuario:shell:home:comentario:crear_home
```

### Campos

- **usuario**: Nombre del usuario a crear
- **shell**: Shell por defecto (ej: /bin/bash, /bin/sh) o `-` para usar el predeterminado
- **home**: Directorio home del usuario o `-` para usar el predeterminado
- **comentario**: Comentario/descripción del usuario o `-` para omitir
- **crear_home**: `yes`, `YES`, `1` para crear el directorio home, o `no`, `NO`, `0` para no crearlo

### Ejemplo de archivo

```
juan:/bin/bash:/home/juan:Juan Pérez:yes
maria:/bin/bash:/home/maria:María García:yes
pedro:/bin/sh:/home/pedro:Pedro López:no
admin:/bin/bash:/home/admin:Administrador del Sistema:yes
```

## Ejemplos de Uso

### Crear usuarios sin contraseña

```bash
sudo ./crear_usuarios.sh -f usuarios_ejemplo.txt
```

### Crear usuarios con contraseña para todos

```bash
sudo ./crear_usuarios.sh -f usuarios_ejemplo.txt -p MiPassword123
```

### Modo verbose (muestra información detallada)

```bash
sudo ./crear_usuarios.sh -f usuarios_ejemplo.txt -p MiPassword123 -v
```

## Características

- ✅ Crea usuarios desde un archivo de configuración
- ✅ Permite especificar shell, directorio home y comentario
- ✅ Opción para crear o no el directorio home
- ✅ Establece contraseña para todos los usuarios si se proporciona
- ✅ Informa el resultado de cada creación (éxito o error)
- ✅ Valida que el script se ejecute como root
- ✅ Ignora usuarios que ya existen
- ✅ Muestra resumen final con estadísticas

## Salida del Script

El script muestra:
- Estado de cada usuario (creado, ya existe, error)
- Resumen final con:
  - Número de usuarios creados exitosamente
  - Número de usuarios que ya existían
  - Número de usuarios con errores

## Notas

- El script debe ejecutarse con permisos de root
- Los usuarios que ya existen se omiten automáticamente
- Si se proporciona una contraseña, se aplica a todos los usuarios
- Las líneas vacías y comentarios (que empiezan con #) se ignoran

