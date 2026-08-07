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

{{- define "worldview.svcUrl" -}}
{{- printf "http://%s:%s" (include "worldview.serviceName" (dict "Release" .Release "name" .name)) (toString (.port | default 8000)) -}}
{{- end -}}