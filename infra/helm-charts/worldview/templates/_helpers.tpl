{{- define "worldview.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "worldview.serviceName" -}}
{{- $name := .name | default "svc" -}}
{{- $k8s := replace "_" "-" $name -}}
{{- printf "%s-%s" .Release.Name $k8s | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "worldview.image" -}}
{{- $root := .root -}}
{{- printf "%s/%s-%s:%s" $root.Values.image.registry $root.Values.image.repository (include "worldview.slug" .service) $root.Values.image.tag -}}
{{- end -}}

{{- /*
  Turn a service key into the image/app slug. `ai_guide` stays underscored because
  the runtime module and container image use `ai_guide`.
*/ -}}
{{- define "worldview.slug" -}}
{{- . -}}
{{- end -}}

{{- define "worldview.k8sName" -}}
{{- replace "_" "-" . -}}
{{- end -}}

{{- /*
  True if a per-service config enables canary via Argo Rollouts.
  Input: a per-service values dict (`.Values.services.<name>`).
*/ -}}
{{- define "worldview.rolloutEnabled" -}}
{{- $cfg := . | default dict -}}
{{- $r := get $cfg "rollout" | default dict -}}
{{- default false $r.enabled -}}
{{- end -}}

{{- define "worldview.svcUrl" -}}
{{- printf "http://%s:%s" (include "worldview.serviceName" (dict "Release" .Release "name" .name)) (toString (.port | default 8000)) -}}
{{- end -}}

{{- /*
  Shared pod spec for Deployments and Argo Rollouts. Input: dict with keys
  root (top-level context), name (service key), cfg (per-service values).
*/ -}}
{{- define "worldview.podTemplate" -}}
template:
  metadata:
    labels:
      app.kubernetes.io/instance: {{ .root.Release.Name }}
      app.kubernetes.io/component: {{ .name }}
  spec:
    serviceAccountName: {{ include "worldview.fullname" .root }}
    securityContext:
      runAsNonRoot: true
    containers:
      - name: {{ include "worldview.k8sName" .name }}
        image: {{ include "worldview.image" (dict "root" .root "service" .name) }}
        imagePullPolicy: {{ .root.Values.image.pullPolicy }}
        ports:
          - name: http
            containerPort: {{ .root.Values.serviceDefaults.port }}
        envFrom:
          - configMapRef:
              name: {{ include "worldview.fullname" .root }}-common
          - secretRef:
              name: {{ include "worldview.fullname" .root }}-credentials
        {{- with .cfg.env }}
        env:
          {{- range $k, $v := . }}
          - name: {{ $k }}
            value: {{ $v | quote }}
          {{- end }}
        {{- end }}
        resources:
          {{- toYaml .root.Values.serviceDefaults.resources | nindent 10 }}
        readinessProbe:
          httpGet:
            path: /healthz
            port: http
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          initialDelaySeconds: 15
          periodSeconds: 15
{{- end -}}
