FROM ubuntu:latest

# Use a build argument for the directory name
ARG DIRECTORY_NAME=zones

# Install BIND
RUN apt-get update && apt-get install -y bind9 bind9utils bind9-doc

# Adjust permissions and ownership for rndc.key
RUN chown bind:bind /etc/bind/rndc.key && chmod 640 /etc/bind/rndc.key

# Copy over your named.conf and zones directory
COPY named.conf /etc/bind/
COPY $DIRECTORY_NAME /etc/bind/

# Expose DNS port
EXPOSE 53/udp
EXPOSE 53/tcp

CMD ["/usr/sbin/named", "-g"]