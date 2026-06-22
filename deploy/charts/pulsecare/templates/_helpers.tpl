{{- define "pulsecare.image" -}}
{{- printf "%s/%s:%s" .root.Values.global.imageRegistry .repository .root.Values.global.imageTag -}}
{{- end -}}
