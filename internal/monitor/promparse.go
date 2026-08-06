package monitor

import (
	"strings"

	dto "github.com/prometheus/client_model/go"
	"github.com/prometheus/common/expfmt"
	"github.com/prometheus/common/model"
)

type Sample struct {
	Labels map[string]string
	Value  float64
}

// ParsePrometheusText parses a Prometheus text exposition into a map of
// metric name -> samples (using the official expfmt parser).
func ParsePrometheusText(text string) (map[string][]Sample, error) {
	parser := expfmt.NewTextParser(model.UTF8Validation)
	families, err := parser.TextToMetricFamilies(strings.NewReader(text))
	if err != nil {
		return nil, err
	}
	out := map[string][]Sample{}
	for name, fam := range families {
		for _, m := range fam.GetMetric() {
			labels := map[string]string{}
			for _, lp := range m.GetLabel() {
				labels[lp.GetName()] = lp.GetValue()
			}
			out[name] = append(out[name], Sample{Labels: labels, Value: sampleValue(m)})
		}
	}
	return out, nil
}

func sampleValue(m *dto.Metric) float64 {
	if g := m.GetGauge(); g != nil {
		return g.GetValue()
	}
	if c := m.GetCounter(); c != nil {
		return c.GetValue()
	}
	if u := m.GetUntyped(); u != nil {
		return u.GetValue()
	}
	if s := m.GetSummary(); s != nil {
		return s.GetSampleSum()
	}
	if h := m.GetHistogram(); h != nil {
		return h.GetSampleSum()
	}
	return 0
}
