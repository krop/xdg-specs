DOCS = sound-naming-spec.html sound-theme-spec.html

%.html: %.xml
	xsltproc http://docbook.sourceforge.net/release/xsl/current/xhtml/docbook.xsl $< > $@

all: $(DOCS)

clean:
	rm -f $(DOCS)
