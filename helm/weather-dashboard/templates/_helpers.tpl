---
{{/*
Expand the name of the chart.
*/}}
{{- define "weather-dashboard.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
*/}}
{{- define "weather-dashboard.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "weather-dashboard.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "weather-dashboard.labels" -}}
helm.sh/chart: {{ include "weather-dashboard.chart" . }}
{{ include "weather-dashboard.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "weather-dashboard.selectorLabels" -}}
app.kubernetes.io/name: {{ include "weather-dashboard.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "weather-dashboard.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "weather-dashboard.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Validate required AWS values
*/}}
{{- define "weather-dashboard.validateAwsValues" -}}
{{- if .Values.serviceAccount.create -}}
{{- if not .Values.aws.accountId }}
{{- fail "AWS account ID (.Values.aws.accountId) is required when creating a service account" -}}
{{- end -}}
{{- if not .Values.aws.iamRole }}
{{- fail "AWS IAM role (.Values.aws.iamRole) is required when creating a service account" -}}
{{- end -}}
{{- end -}}
{{- end -}}