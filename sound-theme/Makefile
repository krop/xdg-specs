DOCS = sound-naming-spec.html sound-theme-spec.html

%.html: %.xml
	xsltproc /usr/share/sgml/docbook/xsl-stylesheets-1.73.2/xhtml/docbook.xsl $< > $@

all: $(DOCS)

clean:
	rm -f $(DOCS)
