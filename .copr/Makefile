# Fedora COPR "make srpm" yöntemi: git deposundan kaynak arşivini ve SRPM'i üretir.
# COPR bu hedefi çağırır ve $(outdir) değişkenini kendisi verir.
outdir ?= .
spec   := packaging/mouse-buttons.spec

srpm:
	dnf -y install git rpm-build
	version=$$(rpmspec -q --qf '%{version}' --srpm $(spec)) && \
	git archive --format=tar.gz --prefix=mouse-buttons-$$version/ \
	    -o $(outdir)/mouse-buttons-$$version.tar.gz HEAD && \
	rpmbuild -bs $(spec) --define "_sourcedir $(outdir)" --define "_srcrpmdir $(outdir)"
