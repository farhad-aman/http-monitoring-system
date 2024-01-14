{{- define "http-monitoring-system.fullname" -}}
{{- printf "%s-%s" .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- define "http-monitoring-system.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- define "http-monitoring-system.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- define "http-monitoring-system.labels" -}}
app.kubernetes.io/name: {{ include "http-monitoring-system.name" . }}
helm.sh/chart: {{ include "http-monitoring-system.chart" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
