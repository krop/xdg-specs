DOCS = sound-naming-spec.html sound-theme-spec.html

%.html: %.xml
	xsltproc /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl $< > $@

all: $(DOCS)

clean:
	rm -f $(DOCS)
