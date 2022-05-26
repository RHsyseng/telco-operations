.DEFAULT_GOAL := install


clean :
	kcli delete plan --yes mycluster
	aicli stop cluster mycluster || true
	aicli delete deployment mycluster
	rm -rf /var/www/html/mycluster.iso

install :
	kcli create plan mycluster
	aicli create deployment mycluster
