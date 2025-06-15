# Use a imagem oficial do Metabase como base
FROM metabase/metabase:latest

# Defina o diretório de plugins
ENV MB_PLUGINS_DIR="/plugins"

# Crie o diretório de plugins
RUN mkdir -p $MB_PLUGINS_DIR

# Baixe o plugin necessário e coloque-o no diretório de plugins
RUN curl -Lso $MB_PLUGINS_DIR/starburst-5.0.0.metabase-driver.jar \
    https://github.com/starburstdata/metabase-driver/releases/download/5.0.0/starburst-5.0.0.metabase-driver.jar

# Exponha a porta padrão do Metabase
EXPOSE 3000

# Comando para iniciar o Metabase
CMD ["java", "-jar", "/app/metabase.jar"]



# docker build -t metabase-custom:latest .
# docker tag metabase-custom:latest brunocza1/metabase-custom:latest
# docker push brunocza1/metabase-custom:latest
