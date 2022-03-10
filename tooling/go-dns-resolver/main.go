package main

import (
	"context"
	"log"
	"net"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	successfulDnsQueries = prometheus.NewCounter(
		prometheus.CounterOpts{
			Name: "dns_successful_queries",
			Help: "Total number of successful dns queries",
		},
	)
)
var (
	unsuccessfulDnsQueries = prometheus.NewCounter(
		prometheus.CounterOpts{
			Name: "dns_unsuccessful_queries",
			Help: "Total number of unsuccessful dns queries",
		},
	)
)

func dnsResolve(domain string, timeout int) {

	timeoutInterval := time.Duration(timeout) * time.Second
	ctx, cancel := context.WithTimeout(context.TODO(), timeoutInterval)
	defer cancel()

	var r net.Resolver
	ips, err := r.LookupIP(ctx, "ip", domain)

	if err != nil {
		log.Printf("IP was not resolved: %v\n", err)
		unsuccessfulDnsQueries.Inc()
	} else {
		successfulDnsQueries.Inc()
		for _, ip := range ips {
			log.Printf("IP resolved: %s\n", ip.String())
		}
	}

}

//getEnv returns the value for a given Env Var
func getEnv(varName string, defaultValue string) string {
	if varValue, ok := os.LookupEnv(varName); ok {
		return varValue
	}
	return defaultValue
}

func listen(port string, registry *prometheus.Registry) {
	log.Printf("Listening on port %s", port)
	http.Handle("/metrics", promhttp.HandlerFor(registry, promhttp.HandlerOpts{}))
	//http.Handle("/metrics", promhttp.Handler()) -> Default prometheus collector, includes other stuff on top of our custom registers
	log.Fatal(http.ListenAndServe(":"+port, nil))
}

func main() {

	port := getEnv("APP_PORT", "9999")
	routines := getEnv("RESOLV_ROUTINES", "1")
	domain := getEnv("RESOLV_DOMAIN", "google.com")
	timeout := getEnv("RESOLV_TIMEOUT", "2")
	waitInterval := getEnv("WAIT_INTERVAL", "2")
	intRoutines, _ := strconv.Atoi(routines)
	intWaitInterval, _ := strconv.Atoi(waitInterval)
	intResolvTimeout, _ := strconv.Atoi(timeout)

	log.Printf("Started with parameters. Port: %s, Routines: %d, Domain: %s, WaitInterval: %d, DnsTimeout: %d", port, intRoutines, domain, intWaitInterval, intResolvTimeout)

	registry := prometheus.NewRegistry()
	registry.MustRegister(successfulDnsQueries)
	registry.MustRegister(unsuccessfulDnsQueries)
	//prometheus.MustRegister(successfulDnsQueries)
	//prometheus.MustRegister(unsuccessfulDnsQueries)
	//prometheus.Unregister(collectors.NewGoCollector()) -> Remove the go collectors from the default prometheus registry
	//prometheus.Unregister(collectors.NewProcessCollector(collectors.ProcessCollectorOpts{})) -> Remove the process collectors from the default prometheus registry

	var wg sync.WaitGroup

	go listen(port, registry)

	for {
		wg.Add(intRoutines)
		start := make(chan struct{})
		for i := 0; i < intRoutines; i++ {
			go func() {
				<-start
				defer wg.Done()
				dnsResolve(domain, intResolvTimeout)
				time.Sleep(time.Duration(intWaitInterval) * time.Second)
			}()
		}
		close(start)
		wg.Wait()
	}
}
