# Script de Creación de Usuarios - Ejercicio 1

Este script permite crear múltiples usuarios en Linux desde un archivo de configuración, desarrollado como parte del ejercicio 1 del obligatorio de Programación para DevOps Linux.

## Requisitos

- Sistema operativo Linux
- Permisos de root (sudo)
- Bash shell

## Uso

```bash
sudo ./ej1_crea_usuarios.sh [-i] [-c contraseña] Archivo_con_los_usuarios_a_crear
```

### Opciones

- `-i`: Muestra información sobre la creación de cada usuario (opcional)
- `-c contraseña`: Asigna la contraseña especificada a todos los usuarios creados (opcional)
- `Archivo_con_los_usuarios_a_crear`: Archivo con la información de usuarios (obligatorio)

## Formato del Archivo de Usuarios

El archivo debe contener un usuario por línea con el siguiente formato (campos separados por `:`):

```
usuario:comentario:directorio_home:crear_home(SI/NO):shell
```

### Campos

- **usuario**: Nombre del usuario a crear (obligatorio)
- **comentario**: Comentario/descripción del usuario (puede estar vacío)
- **directorio_home**: Directorio home del usuario (puede estar vacío para usar el predeterminado)
- **crear_home**: `SI` o `NO` para crear o no el directorio home si no existe (puede estar vacío)
- **shell**: Shell por defecto (ej: /bin/bash, /bin/sh) (puede estar vacío para usar el predeterminado)

**Nota:** Si algún campo está vacío, el script usará los valores por defecto del comando `useradd`.

### Ejemplo de archivo

```
pepe:Este es mi amigo pepe:/home/jose:SI:/bin/bash
papanatas:Este es un usuario trucho:/trucho:NO:/bin/sh
elmaligno::::/bin/el_maligno
```

## Ejemplos de Uso

### Crear usuarios sin contraseña (modo silencioso)

```bash
sudo ./ej1_crea_usuarios.sh Usuarios
```

### Crear usuarios con contraseña

```bash
sudo ./ej1_crea_usuarios.sh -c MiPassword123 Usuarios
```

### Crear usuarios mostrando información detallada

```bash
sudo ./ej1_crea_usuarios.sh -i Usuarios
```

### Crear usuarios con contraseña y mostrar información

```bash
sudo ./ej1_crea_usuarios.sh -i -c MiPassword123 Usuarios
```

## Características

- ✅ Crea usuarios desde un archivo de configuración
- ✅ Permite especificar comentario, directorio home, crear home y shell
- ✅ Opción `-i` para mostrar información detallada de cada creación
- ✅ Opción `-c` para asignar la misma contraseña a todos los usuarios
- ✅ Valida que el script se ejecute como root
- ✅ Ignora usuarios que ya existen
- ✅ Ignora líneas vacías y comentarios (líneas que empiezan con `#`)
- ✅ Valida el formato del archivo (debe tener exactamente 5 campos separados por `:`)
- ✅ Manejo de errores con códigos de retorno específicos

## Salida del Script

### Con la opción `-i`

El script muestra:
- Estado de cada usuario procesado:
  - `Usuario 'nombre' (línea X): Creado exitosamente`
  - `Usuario 'nombre' (línea X): Ya existe, se omite`
  - `Usuario 'nombre' (línea X): ERROR - [descripción del error]`
- Resumen final:
  - `Total de usuarios creados exitosamente: X`

### Sin la opción `-i`

El script ejecuta silenciosamente, solo mostrando errores en stderr.

## Códigos de Retorno

El script utiliza códigos de retorno específicos para diferentes tipos de errores:

- `1`: Archivo no existe
- `2`: Archivo no es un archivo regular
- `3`: Sin permisos de lectura para el archivo
- `4`: Error de sintaxis en el archivo (línea sin exactamente 5 campos)
- `5`: Parámetro incorrecto (modificador inválido o `-c` sin contraseña)
- `6`: Número incorrecto de parámetros (falta el archivo o hay archivos duplicados)
- `7`: Otros errores (no se ejecuta como root, errores al crear usuarios, etc.)
- `0`: Éxito (todos los usuarios se procesaron correctamente)

## Validaciones

El script realiza las siguientes validaciones:

1. **Permisos**: Verifica que se ejecute como root
2. **Archivo**: Verifica que el archivo existe, es regular y tiene permisos de lectura
3. **Formato**: Valida que cada línea tenga exactamente 5 campos separados por `:`
4. **Usuario**: Verifica que el nombre de usuario no esté vacío
5. **Shell**: Verifica que el shell especificado exista (si se proporciona)

## Notas

- El script debe ejecutarse con permisos de root (usar `sudo`)
- Los usuarios que ya existen se omiten automáticamente
- Si se proporciona una contraseña con `-c`, se aplica a todos los usuarios creados
- Las líneas vacías y comentarios (que empiezan con `#`) se ignoran
- Si un campo está vacío, se usa el valor por defecto de `useradd`
- Los mensajes de error se envían a stderr
- El script termina con código de error si encuentra problemas de sintaxis o al crear usuarios

## Ejemplo Completo

Archivo `Usuarios`:
```
pepe:Este es mi amigo pepe:/home/jose:SI:/bin/bash
papanatas:Este es un usuario trucho:/trucho:NO:/bin/sh
elmaligno::::/bin/el_maligno
```

Ejecución:
```bash
sudo ./ej1_crea_usuarios.sh -i -c Password123 Usuarios
```

Salida esperada:
```
Usuario 'pepe' (línea 1): Creado exitosamente
Usuario 'papanatas' (línea 2): Creado exitosamente
Usuario 'elmaligno' (línea 3): Creado exitosamente

Total de usuarios creados exitosamente: 3
```
