FROM docker.io/library/golang:1.16
WORKDIR /go/src/github.com/RHsyseng/telco-operations
COPY main.go .
COPY go.mod .
RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o dns-resolv .

FROM scratch
COPY --from=0 /go/src/github.com/RHsyseng/telco-operations/dns-resolv .
EXPOSE 9999
CMD ["/dns-resolv"]
