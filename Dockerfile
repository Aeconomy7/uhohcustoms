FROM python:3.12.9-alpine

# Upgrade pip and install necessary tools
RUN pip install --upgrade pip && apk add --no-cache curl gcc musl-dev libffi-dev python3-dev openssl-dev py3-virtualenv

# Create a non-root user and set permissions
RUN adduser -D nonroot
WORKDIR /srv/uhohcustoms
RUN mkdir -p /var/log/uhohcustoms && \
    touch /var/log/uhohcustoms/uhohcustoms.err.log && \
    touch /var/log/uhohcustoms/uhohcustoms.out.log && \
    chown -R nonroot:nonroot /var/log/uhohcustoms /srv/uhohcustoms

# Copy and install dependencies before switching users
COPY app .
RUN python3 -m pip install -r requirements.txt

# Copy app files after setting up dependencies
COPY --chown=nonroot:nonroot app . 

# Switch to non-root user
USER nonroot

# Expose port
EXPOSE 2086

# Run the application using Gunicorn
CMD ["gunicorn", "-k", "gevent", "-w", "1", "--bind", "0.0.0.0:2086", "app:app"]
