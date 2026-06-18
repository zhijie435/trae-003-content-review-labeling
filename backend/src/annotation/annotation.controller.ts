import { Controller, Get, Post, Body, Patch, Param, Delete, Query } from '@nestjs/common';
import { AnnotationService } from './annotation.service';
import { CreateAnnotationDto, UpdateAnnotationDto } from './dto/create-annotation.dto';
import { AnnotationType } from './annotation.entity';

@Controller('annotations')
export class AnnotationController {
  constructor(private readonly annotationService: AnnotationService) {}

  @Post()
  create(@Body() createAnnotationDto: CreateAnnotationDto) {
    return this.annotationService.create(createAnnotationDto);
  }

  @Get()
  findAll(@Query('type') type?: AnnotationType) {
    return this.annotationService.findAll(type);
  }

  @Get('review')
  findAllForReview() {
    return this.annotationService.findAllForReview();
  }

  @Get('review/sample')
  getSampleForReview(@Query('count') count?: number) {
    return this.annotationService.getSampleForReview(count);
  }

  @Get('seed')
  seedMockData() {
    return this.annotationService.seedMockData();
  }

  @Get(':id')
  findOne(@Param('id') id: string) {
    return this.annotationService.findOne(+id);
  }

  @Patch(':id')
  update(@Param('id') id: string, @Body() updateAnnotationDto: UpdateAnnotationDto) {
    return this.annotationService.update(+id, updateAnnotationDto);
  }

  @Delete(':id')
  remove(@Param('id') id: string) {
    return this.annotationService.remove(+id);
  }
}
