require 'json'

module Jekyll
  class GaroPageGenerator < Generator
    safe true
    priority :normal

    def generate(site)
      items = load_json(site, '_rawdata/garo.json')

      Jekyll.logger.info "GaroGenerator:", "#{items.size}개 가로수길 페이지 생성 중..."
      items.each do |c|
        next if c['slug'].to_s.strip.empty?
        site.pages << GaroPage.new(site, c)
      end

      Jekyll.logger.info "GaroGenerator:", "완료 (#{items.size}개)"
    end

    private

    def load_json(site, path)
      file = File.join(site.source, path)
      return [] unless File.exist?(file)
      JSON.parse(File.read(file, encoding: 'utf-8'))
    rescue => e
      Jekyll.logger.warn "GaroGenerator:", "#{path} 로드 실패: #{e.message}"
      []
    end
  end

  class GaroPage < Page
    def initialize(site, c)
      @site = site
      @base = site.source
      @dir  = "garo/#{c['slug']}"
      @name = 'index.html'

      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'garo.html')
      self.data.merge!(c)
      self.data['layout']      = 'garo'
      self.data['title']       = build_title(c)
      self.data['description'] = build_desc(c)
    end

    private

    def build_title(c)
      loc = [c['doShort'], c['sigungu']].compact.join(' ')
      "#{c['garoName']} #{loc} 위치 정보"
    end

    def build_desc(c)
      loc = [c['doShort'], c['sigungu']].compact.join(' ')
      "#{loc} #{c['garoName']}의 위치, 수종, 소개 정보를 확인하세요."[0, 155]
    end
  end
end
