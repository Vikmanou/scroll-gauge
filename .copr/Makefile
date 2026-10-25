# COPR runs: make -f .copr/Makefile srpm outdir=<dir> spec=<spec>
spec ?= packaging/scrollgauge.spec
outdir ?= .

srpm:
	dnf -y install rpm-build rpmdevtools
	spectool -g -C $(outdir) $(spec)
	rpmbuild -bs --define "_sourcedir $(outdir)" --define "_srcrpmdir $(outdir)" $(spec)
