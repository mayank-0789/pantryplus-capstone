{{- define "it.labels" -}}
app.kubernetes.io/part-of: pantry
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{- define "it.component" -}}
app.kubernetes.io/name: {{ . }}
{{- end }}

{{- define "it.dbSecretName" -}}
{{- if .Values.postgres.existingSecret }}{{ .Values.postgres.existingSecret }}{{ else }}{{ .Release.Name }}-db{{ end }}
{{- end }}
